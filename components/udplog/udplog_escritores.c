/* L0 udplog — líneas del log por escritor (FR-LOG-02, FR-LOG-03). Núcleo puro. */
#include "udplog_escritores.h"
#include <string.h>

#define LIMITE (UDPLOG_LINEA_MAX - sizeof UDPLOG_MARCA_CORTE)   /* lo que cabe sin cortar */

static void bloquear(udplog_tabla_t *t) { if (t->bloquear) t->bloquear(t->cerrojo); }
static void desbloquear(udplog_tabla_t *t) { if (t->desbloquear) t->desbloquear(t->cerrojo); }

/* Ranura del escritor; si no tiene y `crear`, una libre. NULL si no hay. */
static udplog_ranura_t *ranura(udplog_tabla_t *t, const void *dueno, int crear)
{
    udplog_ranura_t *propia = NULL, *libre = NULL;
    bloquear(t);
    for (int i = 0; i < UDPLOG_RANURAS; i++) {
        if (t->r[i].dueno == dueno) { propia = &t->r[i]; break; }
        if (!libre && !t->r[i].dueno) libre = &t->r[i];
    }
    if (!propia && crear && libre) {
        memset(&libre->acum, 0, sizeof libre->acum);
        libre->dueno = dueno;
        propia = libre;
    }
    desbloquear(t);
    return propia;
}

/* Líneas completas de un trozo sin ranura: salen tal cual (sin \r final, vacías no) */
static int directo(const char *trozo, size_t n, udplog_linea_cb_t cb, void *ctx)
{
    size_t ini = 0;
    for (size_t i = 0; i < n; i++) {
        if (trozo[i] != '\n') continue;
        size_t fin = i;
        while (fin > ini && trozo[fin - 1] == '\r') fin--;
        if (fin > ini) cb(trozo + ini, fin - ini, ctx);
        ini = i + 1;
    }
    return 0;
}

void udplog_escribir(udplog_tabla_t *t, const void *dueno, const char *trozo, size_t n,
                     udplog_linea_cb_t cb, void *ctx)
{
    if (!n) return;
    udplog_ranura_t *r = ranura(t, dueno, 0);
    if (!r) {
        /* ¿Hace falta acumulador? Solo si queda una línea a medias o alguna es demasiado larga */
        size_t ini = 0, ult_nl = 0;
        int hay_nl = 0, larga = 0;
        for (size_t i = 0; i < n; i++) {
            if (trozo[i] == '\n') { if (i - ini > LIMITE) larga = 1; ini = i + 1; ult_nl = i; hay_nl = 1; }
        }
        int cola = !hay_nl || ult_nl != n - 1;
        if (!cola && !larga) { directo(trozo, n, cb, ctx); return; }
        r = ranura(t, dueno, 1);
        if (!r) {
            /* Tabla llena: salen las líneas completas; el trozo final incompleto se descarta */
            if (hay_nl) directo(trozo, ult_nl + 1, cb, ctx);
            t->descartes++;
            return;
        }
    }
    udplog_acumular(&r->acum, trozo, n, cb, ctx);
    if (r->acum.n == 0 && !r->acum.cortada) r->dueno = NULL;   /* sin línea a medias: libre */
}
