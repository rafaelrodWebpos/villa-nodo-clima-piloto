/* TC-OTA-16 · FR-OTA-08, T22 — turno de la descarga (A3-03, auditoría H-91): tras un
 * aborto, mientras la tarea vieja no sale no se admite otra descarga; un intento rechazado
 * no borra el aborto (la tarea vieja no avisa) y la nueva, cuando entra, sí avisa. */
#include <stdio.h>
#include "ota_turno.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    ota_turno_t t = {0};
    ESPERA(!ota_turno_avisar(&t), "sin tarea no hay aviso");
    ota_turno_abortar(&t);
    ESPERA(!t.abortada, "abortar sin tarea no deja marca");

    /* descarga normal: toma, avisa, suelta */
    ESPERA(ota_turno_tomar(&t), "primera descarga");
    ESPERA(!ota_turno_tomar(&t), "segunda a la vez (T21 lo rechaza antes; aquí, defensa)");
    ESPERA(ota_turno_avisar(&t), "termina sin aborto: avisa");
    ota_turno_soltar(&t);
    ESPERA(!t.activa, "suelta");

    /* el escenario de A3-03: T22 aborta, llega otro cmd_ota mientras la vieja sigue en resolver */
    ESPERA(ota_turno_tomar(&t), "descarga A");
    ota_turno_abortar(&t);                                   /* T22 */
    ESPERA(!ota_turno_tomar(&t), "descarga B rechazada mientras A no sale (error:red en main)");
    ESPERA(t.abortada, "el intento de B no borra el aborto de A");
    ESPERA(!ota_turno_avisar(&t), "A, abortada, no llama a fin()");
    ota_turno_soltar(&t);                                    /* A sale */
    ESPERA(ota_turno_tomar(&t), "ahora B entra");
    ESPERA(!t.abortada && ota_turno_avisar(&t), "B empieza sin el aborto de A y avisa al terminar");
    ota_turno_soltar(&t);

    ESPERA(!ota_turno_tomar(NULL) && !ota_turno_avisar(NULL), "NULL");
    ota_turno_abortar(NULL); ota_turno_soltar(NULL);
    printf("TC-OTA-16: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
