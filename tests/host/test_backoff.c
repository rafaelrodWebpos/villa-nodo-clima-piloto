/* TC-CON-02 · FR-CON-02 (host): backoff de reintentos — 1 s, se duplica en cada
 * fallo, techo de 60 s, y vuelve a 1 s tras cada conexión lograda (FSD §6.5, §6.6). */
#include <stdio.h>
#include "conectividad_backoff.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    const unsigned esperado[10] = {1, 2, 4, 8, 16, 32, 60, 60, 60, 60};
    con_backoff_t b;
    con_backoff_reiniciar(&b);
    for (int i = 0; i < 10; i++) {
        unsigned ms = con_backoff_fallo(&b);
        ESPERA(ms == esperado[i] * 1000u, "fallo %d: %u ms, esperado %u s", i + 1, ms, esperado[i]);
        ESPERA(ms <= 60000u, "fallo %d supera 60 s: %u ms", i + 1, ms);
    }
    /* Mil fallos más: nunca pasa del techo ni desborda */
    for (int i = 0; i < 1000; i++) ESPERA(con_backoff_fallo(&b) == 60000u, "fallo %d fuera del techo", 11 + i);
    /* Tras el éxito, 1 s (prohibido: no reiniciar a 1 s) */
    con_backoff_reiniciar(&b);
    unsigned ms = con_backoff_fallo(&b);
    ESPERA(ms == 1000u, "tras el éxito: %u ms", ms);
    printf("TC-CON-02: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
