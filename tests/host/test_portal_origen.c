/* TC-POR-14 · FR-POR-10 (host): el portal solo atiende conexiones cuya dirección local es la
 * IP del AP (192.168.4.1); por la IP del STA en la red doméstica, por 0.0.0.0 o por otra de
 * la red del AP, no (FSD §11.2, SEC-06). */
#include <stdio.h>
#include "portal_origen.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    const uint8_t ap[4] = {192, 168, 4, 1};
    ESPERA(portal_origen_permitido(ap), "192.168.4.1 rechazada");
    const uint8_t no[][4] = {{192, 168, 1, 37}, {10, 0, 0, 5}, {0, 0, 0, 0}, {192, 168, 4, 2},
                             {192, 168, 4, 11}, {1, 4, 168, 192}, {255, 255, 255, 255}};
    for (unsigned i = 0; i < sizeof no / sizeof no[0]; i++)
        ESPERA(!portal_origen_permitido(no[i]), "%u.%u.%u.%u atendida", no[i][0], no[i][1], no[i][2], no[i][3]);
    ESPERA(!portal_origen_permitido(NULL), "NULL atendida");
    printf("TC-POR-14: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
