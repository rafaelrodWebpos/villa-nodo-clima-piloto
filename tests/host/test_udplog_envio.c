/* TC-LOG-06 · FR-LOG-02, FR-LOG-03 (host): reintento del envío UDP (H-57). Un sendto
 * fallido se reintenta hasta 3 veces, con 20 ms entre intentos, sin pasar a la línea
 * siguiente; si sigue fallando, la línea se descarta y se cuenta. Las esperas son solo
 * de la tarea de envío (aquí, la función de espera simulada). */
#include <stdio.h>
#include <string.h>
#include "udplog_envio.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

typedef struct {
    int fallar;               /* cuántos envíos fallan antes de que uno salga (-1: todos) */
    int intentos, esperas;
    unsigned ms_total;
    char salidas[8][32];
    int n_salidas;
} red_t;

static int enviar(const char *l, size_t n, void *ctx)
{
    red_t *r = ctx;
    r->intentos++;
    if (r->fallar < 0) return -1;
    if (r->fallar > 0) { r->fallar--; return -1; }
    if (r->n_salidas < 8) { memcpy(r->salidas[r->n_salidas], l, n); r->salidas[r->n_salidas][n] = 0; }
    r->n_salidas++;
    return (int)n;
}

static void esperar(unsigned ms, void *ctx) { red_t *r = ctx; r->esperas++; r->ms_total += ms; }

int main(void)
{
    red_t r = {0};
    udplog_envio_t e = {.enviar = enviar, .esperar = esperar, .ctx = &r};

    /* Sale a la primera: sin esperas ni contadores */
    ESPERA(udplog_enviar(&e, "a", 1) && r.intentos == 1 && r.esperas == 0, "intentos %d esperas %d", r.intentos, r.esperas);
    ESPERA(e.descartadas == 0 && e.reintentadas == 0, "contadores %u %u", e.descartadas, e.reintentadas);

    /* El caso de la placa: el primer envío tras asociarse falla y el reintento sale */
    r = (red_t){.fallar = 1};
    ESPERA(udplog_enviar(&e, "I (5118) nodo: mqtt: intento 1", 30), "no salió en el reintento");
    ESPERA(r.intentos == 2 && r.esperas == 1 && r.ms_total == 20, "intentos %d esperas %d ms %u", r.intentos, r.esperas, r.ms_total);
    ESPERA(e.reintentadas == 1 && e.descartadas == 0, "contadores %u %u", e.descartadas, e.reintentadas);

    /* Tres fallos: sale en el tercer reintento (4.º intento), 60 ms de espera en total */
    r = (red_t){.fallar = 3};
    ESPERA(udplog_enviar(&e, "b", 1) && r.intentos == 4 && r.ms_total == 60, "intentos %d ms %u", r.intentos, r.ms_total);

    /* Siempre falla: 1 + 3 intentos, 3 esperas de 20 ms, se descarta y se cuenta */
    r = (red_t){.fallar = -1};
    ESPERA(!udplog_enviar(&e, "c", 1), "salió una línea que no podía salir");
    ESPERA(r.intentos == 1 + UDPLOG_REINTENTOS && r.esperas == UDPLOG_REINTENTOS && r.ms_total == 60,
           "intentos %d esperas %d ms %u", r.intentos, r.esperas, r.ms_total);
    ESPERA(e.descartadas == 1, "descartadas %u", e.descartadas);

    /* Orden: con la red caída un momento, la línea 1 sale antes que la 2 (no se adelanta ninguna) */
    r = (red_t){.fallar = 2};
    udplog_enviar(&e, "uno", 3);
    udplog_enviar(&e, "dos", 3);
    ESPERA(r.n_salidas == 2 && strcmp(r.salidas[0], "uno") == 0 && strcmp(r.salidas[1], "dos") == 0,
           "orden %d «%s» «%s»", r.n_salidas, r.salidas[0], r.salidas[1]);

    if (fallos) { printf("%d fallo(s)\n", fallos); return 1; }
    puts("TC-LOG-06: ok");
    return 0;
}
