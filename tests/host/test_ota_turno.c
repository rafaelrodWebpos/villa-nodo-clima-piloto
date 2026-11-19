/* TC-OTA-16 · FR-OTA-08, T22 — turno de la descarga.
 * A3-03 (H-91): tras un aborto, mientras la tarea vieja no sale no se admite otra descarga;
 * un intento rechazado no borra el aborto, la abortada no avisa y la siguiente sí.
 * B-1 (revisión 2026-11-18): un aborto nunca deja arrancable la imagen nueva, llegue antes de
 * esp_https_ota_finish, entre finish y el cierre de la tarea, o después del cierre. */
#include <stdio.h>
#include "ota_turno.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    ota_turno_t t = {0};
    ESPERA(ota_turno_abortar(&t) == OTA_ABORTO_NADA && !t.abortada, "abortar sin tarea no deja marca");
    ESPERA(!ota_turno_puede_finalizar(&t), "sin tarea no se finaliza");

    /* descarga normal: toma, finaliza, avisa, suelta */
    ESPERA(ota_turno_tomar(&t), "primera descarga");
    ESPERA(!ota_turno_tomar(&t), "segunda a la vez");
    ESPERA(ota_turno_puede_finalizar(&t), "sin aborto se finaliza");
    ESPERA(ota_turno_cerrar(&t, true) == OTA_CIERRE_AVISAR, "imagen escrita sin aborto: avisa");
    ota_turno_soltar(&t);
    ESPERA(!t.activa, "suelta");

    /* error de descarga sin aborto: avisa con el error; un T22 posterior no restaura nada */
    ESPERA(ota_turno_tomar(&t), "descarga con error");
    ESPERA(ota_turno_cerrar(&t, false) == OTA_CIERRE_AVISAR, "error: avisa");
    ota_turno_soltar(&t);
    ESPERA(ota_turno_abortar(&t) == OTA_ABORTO_NADA, "sin imagen escrita no hay que restaurar");

    /* A3-03: T22 aborta, llega otro cmd_ota mientras la vieja sigue en resolver */
    ESPERA(ota_turno_tomar(&t), "descarga A");
    ESPERA(ota_turno_abortar(&t) == OTA_ABORTO_EN_CURSO, "T22 con A viva");
    ESPERA(!ota_turno_tomar(&t), "descarga B rechazada mientras A no sale (error:red en main)");
    ESPERA(t.abortada, "el intento de B no borra el aborto de A");
    ESPERA(ota_turno_cerrar(&t, false) == OTA_CIERRE_CALLAR, "A, abortada sin escribir: no avisa");
    ota_turno_soltar(&t);
    ESPERA(ota_turno_tomar(&t), "ahora B entra");
    ESPERA(!t.abortada && ota_turno_puede_finalizar(&t), "B empieza sin el aborto de A");
    ESPERA(ota_turno_cerrar(&t, true) == OTA_CIERRE_AVISAR, "B avisa");
    ota_turno_soltar(&t);
    ESPERA(ota_turno_abortar(&t) == OTA_ABORTO_TARDE, "(B completada; T22 tardío restaura)");

    /* B-1, ventana 1: aborto antes de finish → no se finaliza */
    ESPERA(ota_turno_tomar(&t), "C");
    ota_turno_abortar(&t);
    ESPERA(!ota_turno_puede_finalizar(&t), "abortada antes de finish: no finaliza");
    ESPERA(ota_turno_cerrar(&t, false) == OTA_CIERRE_CALLAR, "C no avisa");
    ota_turno_soltar(&t);
    ESPERA(ota_turno_abortar(&t) == OTA_ABORTO_NADA, "nada que restaurar tras C");

    /* B-1, ventana 2: aborto entre finish y el cierre → la tarea restaura y no avisa */
    ESPERA(ota_turno_tomar(&t), "D");
    ESPERA(ota_turno_puede_finalizar(&t), "D finaliza");
    ESPERA(ota_turno_abortar(&t) == OTA_ABORTO_EN_CURSO, "T22 justo después de finish");
    ESPERA(ota_turno_cerrar(&t, true) == OTA_CIERRE_RESTAURAR, "D restaura el arranque y no avisa");
    ota_turno_soltar(&t);
    ESPERA(ota_turno_abortar(&t) == OTA_ABORTO_NADA, "un segundo T22 no restaura otra vez");

    /* B-1, ventana 3: aborto después del cierre con la imagen escrita → restaura quien aborta, una vez */
    ESPERA(ota_turno_tomar(&t), "E");
    ESPERA(ota_turno_cerrar(&t, true) == OTA_CIERRE_AVISAR, "E avisa ota_ok");
    ota_turno_soltar(&t);
    ESPERA(ota_turno_abortar(&t) == OTA_ABORTO_TARDE, "T22 tras el aviso: el llamante restaura");
    ESPERA(ota_turno_abortar(&t) == OTA_ABORTO_NADA, "solo una vez");
    ESPERA(ota_turno_tomar(&t) && !t.completada, "una descarga nueva limpia la marca");
    ota_turno_soltar(&t);

    ESPERA(!ota_turno_tomar(NULL) && !ota_turno_puede_finalizar(NULL), "NULL");
    ESPERA(ota_turno_abortar(NULL) == OTA_ABORTO_NADA && ota_turno_cerrar(NULL, true) == OTA_CIERRE_CALLAR, "NULL");
    ota_turno_soltar(NULL);
    printf("TC-OTA-16: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
