/* TC-ID-01 · FR-ID-01 (host): id del nodo desde la MAC STA. */
#include <stdio.h>
#include <string.h>
#include "identidad.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    char id[IDENTIDAD_LEN];
    memset(id, 'X', sizeof id);
    /* Contrato: MAC 24:0A:C4:A1:B2:C3 -> clima-a1b2c3 */
    const uint8_t mac[6] = {0x24, 0x0A, 0xC4, 0xA1, 0xB2, 0xC3};
    identidad_desde_mac(mac, id);
    ESPERA(strcmp(id, "clima-a1b2c3") == 0, "id = '%.*s'", IDENTIDAD_LEN, id);
    /* Prohibido: mayúsculas, otro prefijo */
    for (int i = 0; id[i]; i++) ESPERA(!(id[i] >= 'A' && id[i] <= 'Z'), "mayúscula en '%s'", id);
    ESPERA(strncmp(id, "clima-", 6) == 0, "prefijo distinto en '%s'", id);
    /* Solo los 3 últimos bytes; ceros a la izquierda conservados */
    const uint8_t mac2[6] = {0xFF, 0xFF, 0xFF, 0x00, 0x0B, 0xF0};
    identidad_desde_mac(mac2, id);
    ESPERA(strcmp(id, "clima-000bf0") == 0, "id = '%s'", id);
    printf("TC-ID-01: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
