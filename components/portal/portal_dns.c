/* L1 portal — adaptador del DNS cautivo (UDP/53). La respuesta la construye
 * el núcleo puro portal_dns_respuesta (portal_cautivo.c, TC-POR-06). */
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "portal_cautivo.h"
#include "portal_dns.h"
#include "portal_origen.h"

static const char *TAG = "portal";
static volatile bool s_detener;                           /* T24: la tarea sale del bucle */
static char s_ifname[8];                                  /* interfaz lwIP del AP (SO_BINDTODEVICE) */

static void tarea_dns(void *arg)
{
    const int s = (int)(intptr_t)arg;
    /* N-01 (H-85): en lwIP, shutdown() no vale para UDP; con una espera máxima de 1 s el
     * bucle ve s_detener aunque no llegue ninguna consulta */
    const struct timeval espera = {.tv_sec = 1, .tv_usec = 0};
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, &espera, sizeof espera);
    uint8_t q[512], resp[512];
    while (!s_detener) {
        struct sockaddr_in de;
        socklen_t largo = sizeof de;
        int n = recvfrom(s, q, sizeof q, 0, (struct sockaddr *)&de, &largo);
        if (n <= 0) continue;                       /* espera vencida: vuelve a mirar s_detener */
        uint8_t origen[4];
        memcpy(origen, &de.sin_addr.s_addr, 4);
        if (!portal_origen_permitido(PORTAL_IP_AP, origen)) continue;   /* FR-POR-10: solo 192.168.4.0/24 */
        size_t m = portal_dns_respuesta(q, (size_t)n, resp, sizeof resp, PORTAL_IP_AP);
        if (m) sendto(s, resp, m, 0, (struct sockaddr *)&de, largo);
    }
    close(s);
    ESP_LOGI(TAG, "dns detenido");                  /* E14 (FSD 0.9.9) */
    vTaskDelete(NULL);
}

/* T24 (FR-POR-08): la tarea sale del bucle en ≤ 1 s, cierra el socket y escribe E14. */
void portal_dns_detener(void)
{
    s_detener = true;
}

/* N-03 (H-85): el socket se abre y se liga aquí, en T02, para que el resultado sea el real;
 * si falla, E14 «portal: dns no disponible» y el portal sigue sin DNS cautivo. */
static int abrir_socket(void)
{
    /* FR-POR-10 (SEC-06): ligado a la IP del AP, no a INADDR_ANY: en VALIDANDO el nodo
     * también tiene la IP del STA en la red doméstica, y por ahí no se contesta */
    int s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s < 0) return -1;
    struct sockaddr_in dir = {.sin_family = AF_INET, .sin_port = htons(53)};
    memcpy(&dir.sin_addr.s_addr, PORTAL_IP_AP, 4);
    int r = -1;
    for (int i = 0; i < 10 && (r = bind(s, (struct sockaddr *)&dir, sizeof dir)) != 0; i++)
        vTaskDelay(pdMS_TO_TICKS(100));             /* la IP del AP puede tardar en estar lista */
    /* FR-POR-10 (H-85): además, solo por la interfaz del AP. lwIP es de host débil y acepta
     * por el STA un paquete dirigido a 192.168.4.1; udp_input descarta los de otra interfaz */
    if (r == 0 && s_ifname[0]) {
        struct ifreq ifr = {0};
        strlcpy(ifr.ifr_name, s_ifname, sizeof ifr.ifr_name);
        r = setsockopt(s, SOL_SOCKET, SO_BINDTODEVICE, &ifr, sizeof ifr);
    }
    if (r != 0) { close(s); return -1; }
    return s;
}

esp_err_t portal_dns_iniciar(const char *ifname_ap)
{
    if (ifname_ap) strlcpy(s_ifname, ifname_ap, sizeof s_ifname);
    const int s = abrir_socket();
    if (s >= 0 && xTaskCreate(tarea_dns, "portal_dns", 4096, (void *)(intptr_t)s, 5, NULL) == pdPASS)
        return ESP_OK;
    if (s >= 0) close(s);
    ESP_LOGE(TAG, "dns no disponible");              /* E14 (FSD 0.9.9) */
    return ESP_FAIL;
}
