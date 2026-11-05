/* L0 udplog — ensamblado de líneas del log (FR-LOG-02). Núcleo puro. */
#include "udplog_lineas.h"
#include <string.h>

static void emitir(udplog_acum_t *a, udplog_linea_cb_t cb, void *ctx)
{
    size_t n = a->n;
    while (n && a->buf[n - 1] == '\r') n--;
    if (n) cb(a->buf, n, ctx);
    a->n = 0;
}

void udplog_acumular(udplog_acum_t *a, const char *trozo, size_t n, udplog_linea_cb_t cb, void *ctx)
{
    const size_t marca = sizeof UDPLOG_MARCA_CORTE - 1;
    for (size_t i = 0; i < n; i++) {
        char ch = trozo[i];
        if (ch == '\n') {
            if (!a->cortada) emitir(a, cb, ctx);
            a->n = 0;
            a->cortada = 0;
            continue;
        }
        if (a->cortada) continue;
        if (a->n == UDPLOG_LINEA_MAX - 1 - marca) {
            memcpy(a->buf + a->n, UDPLOG_MARCA_CORTE, marca);
            a->n += marca;
            emitir(a, cb, ctx);
            a->cortada = 1;
            continue;
        }
        a->buf[a->n++] = ch;
    }
}
