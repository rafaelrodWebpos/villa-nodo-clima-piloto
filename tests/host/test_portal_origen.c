/* TC-POR-14 · FR-POR-10 (host): el portal solo atiende a clientes de 192.168.4.0/24 que se
 * dirigen a la IP del AP (192.168.4.1). No atiende por la IP del STA ni a un cliente de la
 * red doméstica que llegue a 192.168.4.1 a través del STA (lwIP de host débil) (FSD §11.2,
 * SEC-06, H-85). */
#include <stdio.h>
#include "portal_origen.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    const uint8_t ap[4] = {192, 168, 4, 1}, sta[4] = {192, 168, 1, 37};
    const uint8_t cli_ok[][4] = {{192, 168, 4, 2}, {192, 168, 4, 11}, {192, 168, 4, 254}};
    for (unsigned i = 0; i < sizeof cli_ok / sizeof cli_ok[0]; i++)
        ESPERA(portal_origen_permitido(ap, cli_ok[i]), "cliente 192.168.4.%u rechazado", cli_ok[i][3]);
    /* dirección local distinta de la del AP: la IP del STA, 0.0.0.0, otra de la red del AP */
    const uint8_t locales_no[][4] = {{192, 168, 1, 37}, {0, 0, 0, 0}, {192, 168, 4, 2}, {1, 4, 168, 192}};
    for (unsigned i = 0; i < sizeof locales_no / sizeof locales_no[0]; i++)
        ESPERA(!portal_origen_permitido(locales_no[i], cli_ok[0]), "local %u.%u.%u.%u atendida",
               locales_no[i][0], locales_no[i][1], locales_no[i][2], locales_no[i][3]);
    /* dirigida a 192.168.4.1 pero desde fuera de 192.168.4.0/24: el bypass de host débil */
    const uint8_t remotos_no[][4] = {{192, 168, 1, 50}, {10, 0, 0, 5}, {192, 168, 5, 2}, {192, 168, 3, 2},
                                     {192, 168, 4, 0}, {192, 168, 4, 255}, {192, 168, 4, 1}, {0, 0, 0, 0}};
    for (unsigned i = 0; i < sizeof remotos_no / sizeof remotos_no[0]; i++)
        ESPERA(!portal_origen_permitido(ap, remotos_no[i]), "cliente %u.%u.%u.%u atendido",
               remotos_no[i][0], remotos_no[i][1], remotos_no[i][2], remotos_no[i][3]);
    ESPERA(!portal_origen_permitido(sta, cli_ok[0]), "por la IP del STA");
    ESPERA(!portal_origen_permitido(NULL, cli_ok[0]) && !portal_origen_permitido(ap, NULL), "NULL atendido");
    /* DNS cautivo: además, por la interfaz del AP (IP_PKTINFO; visita del 2026-11-15) */
    const int IF_AP = 2, IF_STA = 1;
    ESPERA(portal_dns_atender(ap, IF_AP, IF_AP, cli_ok[0]), "consulta del iPhone (192.168.4.2 -> 192.168.4.1 por el AP) sin respuesta");
    ESPERA(!portal_dns_atender(ap, IF_STA, IF_AP, cli_ok[0]), "consulta por la interfaz del STA atendida");
    ESPERA(!portal_dns_atender(sta, IF_STA, IF_AP, remotos_no[0]), "consulta a la IP del STA atendida");
    ESPERA(!portal_dns_atender(sta, IF_AP, IF_AP, cli_ok[0]), "consulta del AP a otra IP local atendida");
    ESPERA(!portal_dns_atender(ap, IF_STA, IF_AP, remotos_no[0]), "bypass de host débil por el STA atendido");
    ESPERA(!portal_dns_atender(ap, IF_AP, IF_AP, remotos_no[0]), "origen fuera de 192.168.4.0/24 atendido");
    ESPERA(!portal_dns_atender(ap, 0, 0, cli_ok[0]), "interfaz del AP desconocida (índice 0) atendida");
    ESPERA(!portal_dns_atender(NULL, IF_AP, IF_AP, cli_ok[0]) && !portal_dns_atender(ap, IF_AP, IF_AP, NULL), "NULL atendido");
    printf("TC-POR-14: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
