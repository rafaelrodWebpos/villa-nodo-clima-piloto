/* L2 conectividad — backoff de reintentos (FSD §6.5, FR-CON-02). Núcleo puro. */
#include "conectividad_backoff.h"

#define BASE_MS 1000u
#define TECHO_MS 60000u

void con_backoff_reiniciar(con_backoff_t *b) { b->fallos = 0; }

unsigned con_backoff_fallo(con_backoff_t *b)
{
    /* 1, 2, 4 … s; a partir del 7.º fallo (64 s) ya es el techo: no se desplaza más */
    unsigned ms = b->fallos >= 6 ? TECHO_MS : BASE_MS << b->fallos;
    if (ms > TECHO_MS) ms = TECHO_MS;
    if (b->fallos < 6) b->fallos++;
    return ms;
}
