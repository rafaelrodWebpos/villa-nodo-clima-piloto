/* L0 udplog — ensamblado de líneas del log (FSD §18.1, FR-LOG-02). Núcleo puro:
 * el log llega en trozos; cada línea completa sale una vez, en orden, sin el
 * salto de línea. Una línea demasiado larga sale cortada y marcada. */
#pragma once
#include <stddef.h>

#define UDPLOG_LINEA_MAX 512
#define UDPLOG_MARCA_CORTE " [cortada]"

typedef void (*udplog_linea_cb_t)(const char *linea, size_t n, void *ctx);

typedef struct {
    char   buf[UDPLOG_LINEA_MAX];
    size_t n;
    int    cortada;      /* la línea en curso ya salió cortada: se descarta hasta el '\n' */
} udplog_acum_t;

void udplog_acumular(udplog_acum_t *a, const char *trozo, size_t n, udplog_linea_cb_t cb, void *ctx);
