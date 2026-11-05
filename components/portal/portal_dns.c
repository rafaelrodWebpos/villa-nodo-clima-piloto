/* L1 portal — adaptador del DNS cautivo (UDP/53). La respuesta la construye
 * el núcleo puro portal_dns_respuesta (portal_cautivo.c, TC-POR-06). */
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "portal_cautivo.h"
#include "portal_dns.h"

static const char *TAG = "portal";
static const uint8_t IP_PORTAL[4] = {192, 168, 4, 1};    /* FSD §11.1 */

static void tarea_dns(void *arg)
{
    int s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    struct sockaddr_in dir = {.sin_family = AF_INET, .sin_port = htons(53), .sin_addr.s_addr = htonl(INADDR_ANY)};
    if (s < 0 || bind(s, (struct sockaddr *)&dir, sizeof dir) != 0) {
        ESP_LOGE(TAG, "dns: no se pudo abrir UDP/53");
        if (s >= 0) close(s);
        vTaskDelete(NULL);
        return;
    }
    uint8_t q[512], r[512];
    for (;;) {
        struct sockaddr_in de;
        socklen_t largo = sizeof de;
        int n = recvfrom(s, q, sizeof q, 0, (struct sockaddr *)&de, &largo);
        if (n <= 0) continue;
        size_t m = portal_dns_respuesta(q, (size_t)n, r, sizeof r, IP_PORTAL);
        if (m) sendto(s, r, m, 0, (struct sockaddr *)&de, largo);
    }
}

esp_err_t portal_dns_iniciar(void)
{
    return xTaskCreate(tarea_dns, "portal_dns", 4096, NULL, 5, NULL) == pdPASS ? ESP_OK : ESP_FAIL;
}
