/* L0 udplog — adaptador del log por UDP (FR-LOG-02, FR-LOG-03, E11).
 * Cada línea del log serie se copia, una vez que hay IP de STA, en un datagrama
 * unicast al host:puerto de Kconfig. Cada tarea arma sus líneas en su propio
 * acumulador (udplog_escritores: el driver Wi-Fi escribe algunas en trozos), así
 * que dos tareas que escriben a la vez nunca se mezclan ni se esperan. Nunca
 * bloquea a quien escribe el log: si la cola está llena, esa copia se descarta
 * (FR-LOG-03). */
#include "sdkconfig.h"
#include "udplog.h"

#if CONFIG_NODO_UDP_LOG
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "udplog_envio.h"
#include "udplog_escritores.h"

#define COLA_LINEAS 32

typedef struct { uint16_t n; char txt[UDPLOG_LINEA_MAX]; } linea_t;

static vprintf_like_t s_anterior;
static portMUX_TYPE s_cerrojo = portMUX_INITIALIZER_UNLOCKED;
static void bloquear(void *c) { portENTER_CRITICAL((portMUX_TYPE *)c); }      /* solo la búsqueda de ranura */
static void desbloquear(void *c) { portEXIT_CRITICAL((portMUX_TYPE *)c); }
static udplog_tabla_t s_tabla = {.bloquear = bloquear, .desbloquear = desbloquear, .cerrojo = &s_cerrojo};
static QueueHandle_t s_cola;
static volatile bool s_con_ip;
static volatile unsigned s_cola_llena;                   /* copias descartadas con la cola llena */
static udplog_envio_t s_envio;                           /* reintento y descartadas (H-57) */
static TaskHandle_t s_tarea;

static void encolar(const char *l, size_t n, void *ctx)
{
    (void)ctx;
    if (!s_con_ip) return;                               /* «una vez que tenga IP» */
    linea_t it;
    it.n = (uint16_t)(n < sizeof it.txt ? n : sizeof it.txt);
    memcpy(it.txt, l, it.n);
    if (xQueueSend(s_cola, &it, 0) != pdTRUE) s_cola_llena++;   /* cola llena: se descarta y se cuenta */
}

static int gancho(const char *fmt, va_list ap)
{
    va_list copia;
    va_copy(copia, ap);
    int r = s_anterior(fmt, ap);                         /* la consola serie, como siempre */
    if (s_con_ip && xTaskGetCurrentTaskHandle() != s_tarea) {
        char tmp[UDPLOG_LINEA_MAX];
        int n = vsnprintf(tmp, sizeof tmp, fmt, copia);
        if (n > 0) udplog_escribir(&s_tabla, xTaskGetCurrentTaskHandle(), tmp,
                                   (size_t)(n < (int)sizeof tmp ? n : (int)sizeof tmp - 1), encolar, NULL);
    }
    va_end(copia);
    return r;
}

typedef struct { int s; struct sockaddr_in dest; } destino_t;

static int enviar(const char *linea, size_t n, void *ctx)
{
    destino_t *d = ctx;
    if (d->s < 0) d->s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (d->s < 0) return -1;
    return sendto(d->s, linea, n, MSG_DONTWAIT, (struct sockaddr *)&d->dest, sizeof d->dest);   /* sin log aquí */
}

static void esperar(unsigned ms, void *ctx) { (void)ctx; vTaskDelay(pdMS_TO_TICKS(ms) ? pdMS_TO_TICKS(ms) : 1); }

/* Solo esta tarea espera (los reintentos de H-57); quien escribe el log solo encola */
static void tarea_envio(void *arg)
{
    static destino_t d = {.s = -1, .dest = {.sin_family = AF_INET}};
    d.dest.sin_port = htons(CONFIG_NODO_UDP_LOG_PORT);
    inet_pton(AF_INET, CONFIG_NODO_UDP_LOG_HOST, &d.dest.sin_addr);
    s_envio = (udplog_envio_t){.enviar = enviar, .esperar = esperar, .ctx = &d};
    linea_t it;
    for (;;) {
        if (xQueueReceive(s_cola, &it, portMAX_DELAY) != pdTRUE) continue;
        if (!s_con_ip) continue;
        udplog_enviar(&s_envio, it.txt, it.n);
    }
}

/* H-57: contadores visibles en cada (re)conexión y, si cambiaron, cada 60 s */
static unsigned s_inf_desc, s_inf_reint, s_inf_cola;

static void informar(bool siempre)
{
    unsigned d = s_envio.descartadas, r = s_envio.reintentadas, q = s_cola_llena;
    if (!siempre && d == s_inf_desc && r == s_inf_reint && q == s_inf_cola) return;
    s_inf_desc = d; s_inf_reint = r; s_inf_cola = q;
    ESP_LOGI("nodo", "udplog: descartadas=%u reintentadas=%u cola_llena=%u", d, r, q);
}

static void al_informe(void *arg) { (void)arg; informar(false); }

static void al_evento(void *arg, esp_event_base_t base, int32_t id, void *datos)
{
    if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        xQueueReset(s_cola);
        s_con_ip = true;
        /* E11: la primera línea que sale por UDP tras obtener IP */
        ESP_LOGI("nodo", "UDP logging -> %s:%d", CONFIG_NODO_UDP_LOG_HOST, CONFIG_NODO_UDP_LOG_PORT);
        informar(true);                                  /* H-57: lo perdido desde el arranque */
    } else {
        s_con_ip = false;                                /* sin IP de STA no se envía nada */
    }
}

esp_err_t udplog_iniciar(void)
{
    s_cola = xQueueCreate(COLA_LINEAS, sizeof(linea_t));
    if (!s_cola) return ESP_ERR_NO_MEM;
    if (xTaskCreate(tarea_envio, "udplog", 4096, NULL, 3, &s_tarea) != pdPASS) return ESP_FAIL;
    esp_timer_handle_t t;
    const esp_timer_create_args_t a = {.callback = al_informe, .name = "udplog_inf"};
    ESP_ERROR_CHECK(esp_timer_create(&a, &t));
    ESP_ERROR_CHECK(esp_timer_start_periodic(t, 60 * 1000000ULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, al_evento, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_LOST_IP, al_evento, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, al_evento, NULL));
    s_anterior = esp_log_set_vprintf(gancho);
    return ESP_OK;
}

#else

esp_err_t udplog_iniciar(void) { return ESP_OK; }   /* FR-LOG-01: nada sale por la red */

#endif
