/* L0 udplog — adaptador del log por UDP (FR-LOG-02, FR-LOG-03, E11).
 * Cada línea del log serie se copia, una vez que hay IP de STA, en un datagrama
 * unicast al host:puerto de Kconfig. Nunca bloquea a quien escribe el log: si el
 * mutex está ocupado o la cola llena, esa copia se descarta (FR-LOG-03). */
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
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "udplog_lineas.h"

#define COLA_LINEAS 32

typedef struct { uint16_t n; char txt[UDPLOG_LINEA_MAX]; } linea_t;

static vprintf_like_t s_anterior;
static udplog_acum_t s_acum;
static SemaphoreHandle_t s_mutex;
static QueueHandle_t s_cola;
static volatile bool s_con_ip;
static TaskHandle_t s_tarea;

static void encolar(const char *l, size_t n, void *ctx)
{
    (void)ctx;
    if (!s_con_ip) return;                               /* «una vez que tenga IP» */
    linea_t it;
    it.n = (uint16_t)(n < sizeof it.txt ? n : sizeof it.txt);
    memcpy(it.txt, l, it.n);
    xQueueSend(s_cola, &it, 0);                          /* cola llena: se descarta */
}

static int gancho(const char *fmt, va_list ap)
{
    va_list copia;
    va_copy(copia, ap);
    int r = s_anterior(fmt, ap);                         /* la consola serie, como siempre */
    if (s_con_ip && xTaskGetCurrentTaskHandle() != s_tarea &&
        xSemaphoreTake(s_mutex, 0) == pdTRUE) {
        char tmp[UDPLOG_LINEA_MAX];
        int n = vsnprintf(tmp, sizeof tmp, fmt, copia);
        if (n > 0) udplog_acumular(&s_acum, tmp, (size_t)(n < (int)sizeof tmp ? n : (int)sizeof tmp - 1), encolar, NULL);
        xSemaphoreGive(s_mutex);
    }
    va_end(copia);
    return r;
}

static void tarea_envio(void *arg)
{
    struct sockaddr_in dest = {.sin_family = AF_INET, .sin_port = htons(CONFIG_NODO_UDP_LOG_PORT)};
    inet_pton(AF_INET, CONFIG_NODO_UDP_LOG_HOST, &dest.sin_addr);
    int s = -1;
    linea_t it;
    for (;;) {
        if (xQueueReceive(s_cola, &it, portMAX_DELAY) != pdTRUE) continue;
        if (!s_con_ip) continue;
        if (s < 0) s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (s >= 0) sendto(s, it.txt, it.n, MSG_DONTWAIT, (struct sockaddr *)&dest, sizeof dest);   /* sin log aquí */
    }
}

static void al_evento(void *arg, esp_event_base_t base, int32_t id, void *datos)
{
    if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        xQueueReset(s_cola);
        s_con_ip = true;
        /* E11: la primera línea que sale por UDP tras obtener IP */
        ESP_LOGI("nodo", "UDP logging -> %s:%d", CONFIG_NODO_UDP_LOG_HOST, CONFIG_NODO_UDP_LOG_PORT);
    } else {
        s_con_ip = false;                                /* sin IP de STA no se envía nada */
    }
}

esp_err_t udplog_iniciar(void)
{
    s_mutex = xSemaphoreCreateMutex();
    s_cola = xQueueCreate(COLA_LINEAS, sizeof(linea_t));
    if (!s_mutex || !s_cola) return ESP_ERR_NO_MEM;
    if (xTaskCreate(tarea_envio, "udplog", 4096, NULL, 3, &s_tarea) != pdPASS) return ESP_FAIL;
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, al_evento, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_LOST_IP, al_evento, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, al_evento, NULL));
    s_anterior = esp_log_set_vprintf(gancho);
    return ESP_OK;
}

#else

esp_err_t udplog_iniciar(void) { return ESP_OK; }   /* FR-LOG-01: nada sale por la red */

#endif
