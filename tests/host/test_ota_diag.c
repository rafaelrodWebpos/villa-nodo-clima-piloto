/* TC-OTA-05 · FR-MQTT-09 (host): el campo `ota` de `status` arranca en «ninguno», solo
 * admite los valores de §9.3, y un cambio se publica ya si hay conexión (OPERATIVO) o va
 * en el primer `status` de T11 si no la hay (T22); el mismo valor no cuenta como cambio. */
#include <stdio.h>
#include <string.h>
#include "ota_diag.h"
#include "ota_politica.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    ota_diag_t d;
    ota_diag_iniciar(&d);
    ESPERA(strcmp(d.valor, "ninguno") == 0, "inicial: %s", d.valor);
    /* T17 en OPERATIVO: en_curso, publicar ya */
    ESPERA(ota_diag_cambiar(&d, "en_curso", true) == OTA_DIAG_PUBLICAR_YA && strcmp(d.valor, "en_curso") == 0, "en_curso");
    /* el mismo valor otra vez no es un cambio (ni E7 ni status) */
    ESPERA(ota_diag_cambiar(&d, "en_curso", true) == OTA_DIAG_SIN_CAMBIO, "repetido");
    /* T22 sin conexión: error:red va con T11; nunca se queda en en_curso */
    ESPERA(ota_diag_cambiar(&d, "error:red", false) == OTA_DIAG_CON_T11 && strcmp(d.valor, "error:red") == 0, "T22");
    /* valores no de §9.3: no cambian nada */
    const char *malos[] = {"", "OK", "rechazado:", "error:otra", "rechazado:host ", NULL};
    for (size_t i = 0; i < sizeof malos / sizeof malos[0]; i++)
        ESPERA(ota_diag_cambiar(&d, malos[i], true) == OTA_DIAG_INVALIDO && strcmp(d.valor, "error:red") == 0,
               "«%s» aceptado", malos[i] ? malos[i] : "NULL");
    /* todos los motivos de la política son valores válidos de §9.3 */
    for (int m = OTA_OK; m <= OTA_ERROR_RED; m++) {
        const char *t = m == OTA_OK ? "ok" : ota_motivo_texto((ota_motivo_t)m);
        ESPERA(ota_diag_valido(t), "motivo %s no es de §9.3", t);
    }
    ESPERA(ota_diag_cambiar(&d, "rechazado:version_anterior", true) == OTA_DIAG_PUBLICAR_YA, "el valor más largo cabe");
    ESPERA(strlen("rechazado:version_anterior") < OTA_DIAG_MAX, "OTA_DIAG_MAX");
    printf("TC-OTA-05: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
