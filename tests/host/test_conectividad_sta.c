/* TC-CON-13 · FR-CON-07 (host): con clave, el STA exige WPA2-PSK como mínimo y anuncia
 * PMF capaz; con clave vacía admite una red abierta (FSD §6.5, §6.6, SEC-07). */
#include <stdio.h>
#include "conectividad_sta.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    const char *con_clave[] = {"12345678", "clave-de-prueba-larga", "123456789012345678901234567890123456789012345678901234567890123"};
    for (unsigned i = 0; i < sizeof con_clave / sizeof con_clave[0]; i++) {
        con_sta_seguridad_t s = con_sta_seguridad(con_clave[i]);
        ESPERA(s.umbral == CON_STA_UMBRAL_WPA2_PSK, "con clave %u: umbral %d (No debe: abierta)", i, s.umbral);
        ESPERA(s.pmf_capaz, "con clave %u: PMF no capaz", i);
        ESPERA(!s.pmf_requerido, "con clave %u: PMF requerido (dejaría fuera routers sin PMF)", i);
    }
    con_sta_seguridad_t v = con_sta_seguridad("");
    ESPERA(v.umbral == CON_STA_UMBRAL_ABIERTA, "clave vacía: umbral %d", v.umbral);
    ESPERA(v.pmf_capaz && !v.pmf_requerido, "clave vacía: PMF %d/%d", v.pmf_capaz, v.pmf_requerido);
    con_sta_seguridad_t n = con_sta_seguridad(NULL);
    ESPERA(n.umbral == CON_STA_UMBRAL_ABIERTA, "clave NULL: umbral %d", n.umbral);
    printf("TC-CON-13: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
