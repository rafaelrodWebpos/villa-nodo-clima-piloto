/* TC-TIME-02 · FR-TIME-02 (host): regla de validez de la hora (§13) y fecha de build.
 * TC-TIME-07 · FR-TIME-04, FR-TIME-06 (host): planificador de peticiones SNTP.
 * argv[1] elige el test. */
#include <stdio.h>
#include <string.h>
#include "hora.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

static void time02(void)
{
    const int64_t build = hora_build_epoch("Nov  7 2026", "20:33:08");
    ESPERA(build == 1794083588, "build = %lld", (long long)build);       /* 2026-11-07T20:33:08Z */
    /* Las cuatro filas del contrato host de FR-TIME-02 */
    ESPERA(!hora_es_valida(false, 1893456000, build), "sin sincronizar y reloj en 2030: no válida");
    ESPERA(!hora_es_valida(true, 0, build), "sincronizado y reloj en 1970: no válida");
    ESPERA(!hora_es_valida(true, build - 1, build), "sincronizado y build − 1 s: no válida");
    ESPERA(hora_es_valida(true, build + 1, build), "sincronizado y build + 1 s: válida");
    ESPERA(hora_es_valida(true, build, build), "sincronizado y justo la fecha de build: válida");
    /* Fecha de build ilegible: nunca válida */
    ESPERA(hora_build_epoch("Foo  7 2026", "20:33:08") == -1, "mes desconocido");
    ESPERA(hora_build_epoch("Nov  7 2026", "2033:08") == -1, "hora mal formada");
    ESPERA(!hora_es_valida(true, 1893456000, -1), "build ilegible: no válida");
    ESPERA(hora_build_epoch("Jan  1 1970", "00:00:00") == 0, "epoch 0");
    ESPERA(hora_build_epoch("Feb 29 2028", "12:00:00") == 1835438400, "bisiesto");
    printf("TC-TIME-02: %s\n", fallos ? "FALLO" : "ok");
}

static void time07(void)
{
    hora_sntp_t h;
    hora_iniciar(&h);
    /* FR-TIME-06: sin hora, una petición en cada tick (15 s); el intento falla a los 30 s y sigue pidiendo */
    unsigned esperado[] = {HORA_PEDIR, HORA_PEDIR, HORA_FALLO | HORA_PEDIR, HORA_PEDIR, HORA_FALLO | HORA_PEDIR};
    for (int i = 0; i < 5; i++) {
        unsigned a = hora_tick(&h, (int64_t)i * HORA_TICK_MS);
        ESPERA(a == esperado[i], "sin hora, tick %d: acciones %u, esperado %u", i, a, esperado[i]);
    }
    int pedidas = 0;
    for (int i = 5; i < 25; i++) pedidas += (hora_tick(&h, (int64_t)i * HORA_TICK_MS) & HORA_PEDIR) != 0;
    ESPERA(pedidas == 20, "sin hora: %d peticiones en 20 ticks", pedidas);
    /* Sincroniza: sin peticiones hasta 1 h después */
    int64_t t = 25 * HORA_TICK_MS;
    hora_sincronizada(&h, t);
    int antes = 0;
    for (int64_t x = t + HORA_TICK_MS; x < t + HORA_RESYNC_MS; x += HORA_TICK_MS) antes += hora_tick(&h, x) != HORA_NADA;
    ESPERA(antes == 0, "con hora: %d acciones antes de 1 h", antes);
    /* FR-TIME-04: a la hora, intento de resincronización; falla a los 30 s; no invalida; siguiente en 1 h */
    int64_t r = t + HORA_RESYNC_MS;
    ESPERA(hora_tick(&h, r) == HORA_PEDIR, "resincronización a la hora");
    ESPERA(hora_tick(&h, r + HORA_TICK_MS) == HORA_PEDIR, "segunda petición del intento");
    ESPERA(hora_tick(&h, r + 2 * HORA_TICK_MS) == HORA_FALLO, "fallo a los 30 s, sin pedir otra vez");
    ESPERA(h.sincronizado, "un fallo de resincronización no invalida la hora");
    ESPERA(hora_tick(&h, r + 3 * HORA_TICK_MS) == HORA_NADA, "tras el fallo, nada hasta la hora siguiente");
    ESPERA(hora_tick(&h, r + 2 * HORA_TICK_MS + HORA_RESYNC_MS) == HORA_PEDIR, "nuevo intento 1 h después del fallo");
    /* Un nuevo arranque empieza sin hora (FR-TIME-02: sincronización de este arranque) */
    hora_iniciar(&h);
    ESPERA(!h.sincronizado && hora_tick(&h, 0) == HORA_PEDIR, "arranque nuevo: sin hora y pide");
    printf("TC-TIME-07: %s\n", fallos ? "FALLO" : "ok");
}

int main(int argc, char **argv)
{
    const char *q = argc > 1 ? argv[1] : "";
    if (!strcmp(q, "time02")) time02();
    else if (!strcmp(q, "time07")) time07();
    else { time02(); time07(); }
    return fallos ? 1 : 0;
}
