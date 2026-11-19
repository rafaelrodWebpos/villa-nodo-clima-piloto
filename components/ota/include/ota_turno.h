/* L2 ota — turno de la descarga (A3-03 de H-91; B-1 de la revisión del 2026-11-18). Núcleo puro.
 * Solo una tarea de descarga a la vez: tras un aborto (T22) la tarea vieja puede seguir
 * hasta 30 s dentro de la conexión; mientras no salga, no se admite otra (el adaptador
 * devuelve false y main lo trata como T20 con error:red). El aviso de fin solo se da si
 * la descarga no se abortó, y un intento rechazado no borra el aborto pendiente.
 * B-1: un aborto nunca deja como arrancable la imagen nueva. Antes de esp_https_ota_finish
 * se mira el aborto; si llega después de finish, quien lo vea (la tarea al cerrar, o
 * ota_descarga_abortar si la tarea ya cerró con la imagen escrita) devuelve el arranque a la
 * partición en ejecución. Todas las funciones se llaman bajo el cerrojo del adaptador. */
#pragma once
#include <stdbool.h>

typedef struct {
    bool activa;      /* hay una tarea de descarga viva */
    bool abortada;    /* la tarea viva tiene que salir sin avisar */
    bool completada;  /* la última descarga cerró con la imagen escrita y arrancable */
} ota_turno_t;

typedef enum {
    OTA_ABORTO_NADA,        /* no hay descarga: nada que hacer */
    OTA_ABORTO_EN_CURSO,    /* la tarea viva saldrá sin avisar y sin dejar la imagen arrancable */
    OTA_ABORTO_TARDE,       /* la descarga ya cerró con la imagen escrita: el llamante restaura el arranque */
} ota_aborto_t;

typedef enum {
    OTA_CIERRE_AVISAR,      /* llamar a fin() con el resultado */
    OTA_CIERRE_CALLAR,      /* abortada sin imagen escrita: no avisar */
    OTA_CIERRE_RESTAURAR,   /* abortada con la imagen ya escrita: restaurar el arranque y no avisar */
} ota_cierre_t;

/* true: la descarga nueva toma el turno (activa, sin aborto). false: hay otra viva. */
bool ota_turno_tomar(ota_turno_t *t);
/* T22. Ver ota_aborto_t. */
ota_aborto_t ota_turno_abortar(ota_turno_t *t);
/* Justo antes de esp_https_ota_finish: ¿se puede escribir el arranque? (no, si se abortó). */
bool ota_turno_puede_finalizar(const ota_turno_t *t);
/* La tarea, al terminar: qué hacer. imagen_escrita = esp_https_ota_finish devolvió ESP_OK. */
ota_cierre_t ota_turno_cerrar(ota_turno_t *t, bool imagen_escrita);
/* La tarea sale: libera el turno (completada se conserva hasta el siguiente tomar). */
void ota_turno_soltar(ota_turno_t *t);
