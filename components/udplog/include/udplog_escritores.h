/* L0 udplog — líneas del log por escritor (FSD §18.1, FR-LOG-02, FR-LOG-03). Núcleo puro.
 *
 * Con CONFIG_LOG_VERSION=1 cada ESP_LOGx llega al gancho de vprintf en una sola llamada,
 * pero el driver Wi-Fi (libnet80211) escribe algunas líneas en trozos: el prefijo
 * «I (t) wifi:» y el texto en llamadas separadas (medido en la placa el 2026-11-07, 3 por
 * arranque, tarea «wifi», H-55). Si otra tarea escribe entre los dos trozos, un único
 * acumulador compartido mezclaría las líneas. Aquí cada escritor (la tarea) tiene su
 * propio acumulador, que solo ocupa una ranura mientras tiene una línea a medias; las
 * líneas completas salen directamente.
 *
 * Nunca bloquea al escritor (FR-LOG-03): el cerrojo solo protege la búsqueda de ranura
 * (en la placa, una sección crítica de microsegundos, sin esperas). Sin ranura libre, el
 * trozo incompleto se descarta y se cuenta; nunca se mezcla con la línea de otro. */
#pragma once
#include <stddef.h>
#include "udplog_lineas.h"

#define UDPLOG_RANURAS 8

typedef struct {
    const void   *dueno;    /* escritor con una línea a medias; NULL = libre */
    udplog_acum_t acum;
} udplog_ranura_t;

typedef struct {
    udplog_ranura_t r[UDPLOG_RANURAS];
    void (*bloquear)(void *cerrojo);       /* opcionales: sin ellos, un solo hilo */
    void (*desbloquear)(void *cerrojo);
    void *cerrojo;
    volatile unsigned descartes;           /* trozos incompletos sin ranura libre */
} udplog_tabla_t;

/* Pasa un trozo del escritor `dueno`: cada línea completa de ese escritor sale por cb
 * una vez, entera y en orden; nunca junta texto de dos escritores en una línea. */
void udplog_escribir(udplog_tabla_t *t, const void *dueno, const char *trozo, size_t n,
                     udplog_linea_cb_t cb, void *ctx);
