/* L2 hora — regla de validez de la hora (FR-TIME-02) y planificador de las
 * peticiones SNTP (FR-TIME-04, FR-TIME-06). Núcleo puro, sin ESP-IDF; lo
 * compila tests/host. El adaptador (main.c) llama a hora_tick() cada
 * HORA_TICK_MS mientras el nodo tiene IP y ejecuta lo que devuelve. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

#define HORA_TICK_MS        10000      /* FR-TIME-06: una petición cada ≤ 15 s sin hora válida (10 s: margen, H-71); divide a HORA_INTENTO_MS */
#define HORA_INTENTO_MS     30000      /* FR-TIME-04: un intento falla a los 30 s sin respuesta */
#define HORA_RESYNC_MS    3600000      /* FR-TIME-04: resincronizar cada 1 h */

/* FR-TIME-02: válida solo si hubo sincronización en este arranque y el reloj
 * no es anterior a la fecha de build (segundos epoch UTC). */
bool hora_es_valida(bool sincronizado, int64_t reloj, int64_t build);

/* Fecha de build de esp_app_desc_t («Nov  7 2026», «20:33:08») a epoch UTC; −1 si no se entiende. */
int64_t hora_build_epoch(const char *fecha, const char *hora);

typedef struct {
    bool sincronizado;      /* sincronización completada en este arranque */
    bool intento;           /* hay un intento en curso */
    int64_t inicio_ms;      /* inicio del intento en curso */
    int64_t ref_ms;         /* última sincronización o último intento de resincronización fallido */
} hora_sntp_t;

typedef enum {
    HORA_NADA = 0,
    HORA_PEDIR = 1,         /* enviar una petición SNTP (E6 «sntp: inicio <srv>») */
    HORA_FALLO = 2,         /* el intento en curso falló (E6 «sntp: fallo») */
} hora_accion_t;           /* bits: HORA_FALLO | HORA_PEDIR */

void hora_iniciar(hora_sntp_t *h);
/* Un tick con IP; devuelve las acciones (bits) a ejecutar en orden: fallo, luego pedir. */
unsigned hora_tick(hora_sntp_t *h, int64_t ahora_ms);
/* El servidor respondió y el reloj quedó puesto. */
void hora_sincronizada(hora_sntp_t *h, int64_t ahora_ms);
