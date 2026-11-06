/* TC-DIAG-01 · FR-MQTT-08 (campo `reset` de §9.3, también en E1 de §18) (host):
 * cada causa de reinicio tiene el nombre de §9.3 (FSD 0.9.4) y lo desconocido es «otro». */
#include <stdio.h>
#include <string.h>
#include "diag_reset.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    const struct { diag_reset_t c; const char *n; } v[] = {
        {DIAG_RESET_POWERON, "poweron"}, {DIAG_RESET_EXT, "ext"}, {DIAG_RESET_SW, "sw"},
        {DIAG_RESET_PANIC, "panic"}, {DIAG_RESET_TASK_WDT, "task_wdt"}, {DIAG_RESET_INT_WDT, "int_wdt"},
        {DIAG_RESET_WDT, "wdt"}, {DIAG_RESET_DEEPSLEEP, "deepsleep"}, {DIAG_RESET_BROWNOUT, "brownout"},
        {DIAG_RESET_USB, "usb"}, {DIAG_RESET_JTAG, "jtag"}, {DIAG_RESET_OTRO, "otro"},
    };
    for (size_t i = 0; i < sizeof v / sizeof *v; i++)
        ESPERA(strcmp(diag_reset_nombre(v[i].c), v[i].n) == 0, "%d -> '%s', esperado '%s'", (int)v[i].c, diag_reset_nombre(v[i].c), v[i].n);
    /* Un valor fuera de la enumeración no produce NULL ni un nombre inventado */
    ESPERA(strcmp(diag_reset_nombre((diag_reset_t)999), "otro") == 0, "fuera de rango -> '%s'", diag_reset_nombre((diag_reset_t)999));
    ESPERA(strcmp(diag_reset_nombre((diag_reset_t)-1), "otro") == 0, "negativo -> '%s'", diag_reset_nombre((diag_reset_t)-1));
    printf("TC-DIAG-01: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
