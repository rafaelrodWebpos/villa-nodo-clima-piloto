/* L0 udplog — envío de una línea con reintento (FSD §18.1, FR-LOG-02, FR-LOG-03; H-57).
 * Núcleo puro. Justo después de asociarse al AP, el primer sendto no bloqueante puede
 * fallar (medido en la placa el 2026-11-07: 3 de 5 arranques, la línea «mqtt: intento 1»).
 * Solo la tarea de envío reintenta: hasta UDPLOG_REINTENTOS veces, con UDPLOG_ESPERA_MS
 * entre intentos, sin pasar a la línea siguiente (se conserva el orden). Si sigue
 * fallando, la línea se descarta y se cuenta. Quien escribe el log nunca espera: solo
 * encola (FR-LOG-03). */
#pragma once
#include <stdbool.h>
#include <stddef.h>

#define UDPLOG_REINTENTOS 3
#define UDPLOG_ESPERA_MS  20

typedef int  (*udplog_enviar_fn)(const char *linea, size_t n, void *ctx);   /* < 0: fallo */
typedef void (*udplog_esperar_fn)(unsigned ms, void *ctx);

typedef struct {
    udplog_enviar_fn  enviar;
    udplog_esperar_fn esperar;
    void             *ctx;
    unsigned          descartadas;      /* líneas perdidas tras agotar los reintentos */
    unsigned          reintentadas;     /* líneas que salieron en un reintento */
} udplog_envio_t;

/* Envía la línea; true si salió (a la primera o en un reintento) */
bool udplog_enviar(udplog_envio_t *e, const char *linea, size_t n);
