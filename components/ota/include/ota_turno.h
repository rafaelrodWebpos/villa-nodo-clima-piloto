/* L2 ota — turno de la descarga (A3-03, auditoría H-91). Núcleo puro.
 * Solo una tarea de descarga a la vez: tras un aborto (T22) la tarea vieja puede seguir
 * hasta 30 s dentro de la conexión; mientras no salga, no se admite otra (el adaptador
 * devuelve false y main lo trata como T20 con error:red). El aviso de fin (s_fin) solo
 * se da si la descarga no se abortó, y un intento rechazado no borra el aborto pendiente. */
#pragma once
#include <stdbool.h>

typedef struct {
    bool activa;      /* hay una tarea de descarga viva */
    bool abortada;    /* la tarea viva tiene que salir sin avisar */
} ota_turno_t;

/* true: la descarga nueva toma el turno (activa, sin aborto). false: hay otra viva. */
bool ota_turno_tomar(ota_turno_t *t);
/* T22: la tarea viva sale sin avisar. Sin tarea viva no hace nada. */
void ota_turno_abortar(ota_turno_t *t);
/* La tarea, al terminar: ¿llama a fin()? (no, si se abortó). */
bool ota_turno_avisar(const ota_turno_t *t);
/* La tarea sale: libera el turno. */
void ota_turno_soltar(ota_turno_t *t);
