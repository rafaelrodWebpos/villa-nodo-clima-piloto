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
static portal_indice_ap_t s_indice_ap;                    /* índice lwIP de la interfaz del AP */

/* Destino e interfaz de entrada del datagrama (IP_PKTINFO). false si no vienen. */
static bool info_paquete(struct msghdr *msg, uint8_t destino[4], int *if_entrada)
{
    for (struct cmsghdr *c = CMSG_FIRSTHDR(msg); c; c = CMSG_NXTHDR(msg, c)) {
        if (c->cmsg_level == IPPROTO_IP && c->cmsg_type == IP_PKTINFO) {
            const struct in_pktinfo *pi = (const struct in_pktinfo *)CMSG_DATA(c);
            memcpy(destino, &pi->ipi_addr.s_addr, 4);
            *if_entrada = (int)pi->ipi_ifindex;
            return true;
        }
    }
    return false;
}

static void tarea_dns(void *arg)
{
    const int s = (int)(intptr_t)arg;
    /* N-01 (H-85): en lwIP, shutdown() no vale para UDP; con una espera máxima de 1 s el
     * bucle ve s_detener aunque no llegue ninguna consulta */
    const struct timeval espera = {.tv_sec = 1, .tv_usec = 0};
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, &espera, sizeof espera);
    uint8_t q[512], resp[512];
    uint8_t control[CMSG_SPACE(sizeof(struct in_pktinfo))];
    while (!s_detener) {
        struct sockaddr_in de;
        struct iovec iov = {.iov_base = q, .iov_len = sizeof q};
        struct msghdr msg = {.msg_name = &de, .msg_namelen = sizeof de, .msg_iov = &iov, .msg_iovlen = 1,
                             .msg_control = control, .msg_controllen = sizeof control};
        int n = recvmsg(s, &msg, 0);
        if (n <= 0) continue;                       /* espera vencida: vuelve a mirar s_detener */
        uint8_t origen[4], destino[4];
        int if_entrada = 0;
        memcpy(origen, &de.sin_addr.s_addr, 4);
        /* FR-POR-10 (SEC-06): solo a 192.168.4.1, por la interfaz del AP y desde 192.168.4.0/24;
         * sin IP_PKTINFO no se contesta */
        if (!info_paquete(&msg, destino, &if_entrada) ||
            !portal_dns_atender(destino, if_entrada, s_indice_ap ? s_indice_ap() : 0, origen)) continue;
        size_t m = portal_dns_respuesta(q, (size_t)n, resp, sizeof resp, PORTAL_IP_AP);
        if (m) sendto(s, resp, m, 0, (struct sockaddr *)&de, sizeof de);
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
 * si falla, E14 «portal: dns no disponible» y el portal sigue sin DNS cautivo.
 * FR-POR-10 (SEC-06) se aplica por datagrama con IP_PKTINFO (destino e interfaz de entrada) y
 * no ligando el socket a 192.168.4.1 y a la interfaz del AP: así ligado, el iPhone no recibía
 * respuesta (visita del 2026-11-15) y el nombre de la interfaz se leía antes de que existiera. */
static int abrir_socket(void)
{
    int s = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (s < 0) return -1;
    struct sockaddr_in dir = {.sin_family = AF_INET, .sin_port = htons(53), .sin_addr.s_addr = htonl(INADDR_ANY)};
    const int si = 1;
    if (bind(s, (struct sockaddr *)&dir, sizeof dir) != 0 ||
        setsockopt(s, IPPROTO_IP, IP_PKTINFO, &si, sizeof si) != 0) { close(s); return -1; }
    return s;
}

esp_err_t portal_dns_iniciar(portal_indice_ap_t indice_ap)
{
    s_indice_ap = indice_ap;
    s_detener = false;
    const int s = abrir_socket();
    if (s >= 0 && xTaskCreate(tarea_dns, "portal_dns", 4096, (void *)(intptr_t)s, 5, NULL) == pdPASS)
        return ESP_OK;
    if (s >= 0) close(s);
    ESP_LOGE(TAG, "dns no disponible");              /* E14 (FSD 0.9.9) */
    return ESP_FAIL;
}
