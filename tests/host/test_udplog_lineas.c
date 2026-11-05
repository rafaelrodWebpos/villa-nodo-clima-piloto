/* TC-LOG-02 · FR-LOG-02 (host): cada línea del log sale una vez, completa y en
 * orden, aunque llegue en trozos; sin el salto de línea; vacías no; una línea
 * demasiado larga sale cortada y marcada, y lo que sobra no contamina la siguiente. */
#include <stdio.h>
#include <string.h>
#include "udplog_lineas.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

static char salida[8][UDPLOG_LINEA_MAX + 16];
static int n_salida;
static void recoger(const char *l, size_t n, void *ctx)
{
    (void)ctx;
    if (n_salida < 8) { memcpy(salida[n_salida], l, n); salida[n_salida][n] = 0; }
    n_salida++;
}
static void pasar(udplog_acum_t *a, const char *s) { udplog_acumular(a, s, strlen(s), recoger, NULL); }

int main(void)
{
    udplog_acum_t a = {0};
    pasar(&a, "I (1) nodo: ho");
    ESPERA(n_salida == 0, "salió una línea incompleta");
    pasar(&a, "la\r\nI (2) nodo: x\n");
    ESPERA(n_salida == 2, "%d líneas", n_salida);
    ESPERA(strcmp(salida[0], "I (1) nodo: hola") == 0, "'%s'", salida[0]);
    ESPERA(strcmp(salida[1], "I (2) nodo: x") == 0, "'%s'", salida[1]);

    n_salida = 0;
    pasar(&a, "\n\n");
    ESPERA(n_salida == 0, "salieron líneas vacías");

    /* Demasiado larga: sale cortada y marcada; el resto se descarta hasta el '\n' */
    n_salida = 0;
    char larga[UDPLOG_LINEA_MAX * 2];
    memset(larga, 'x', sizeof larga - 1); larga[sizeof larga - 1] = 0;
    pasar(&a, larga);
    pasar(&a, "fin\nI (3) nodo: siguiente\n");
    ESPERA(n_salida == 2, "%d líneas tras la larga", n_salida);
    size_t lm = strlen(UDPLOG_MARCA_CORTE);
    ESPERA(strlen(salida[0]) == UDPLOG_LINEA_MAX - 1, "longitud de la cortada %zu", strlen(salida[0]));
    ESPERA(strcmp(salida[0] + strlen(salida[0]) - lm, UDPLOG_MARCA_CORTE) == 0, "sin la marca de corte");
    ESPERA(strcmp(salida[1], "I (3) nodo: siguiente") == 0, "lo que sobró contaminó la siguiente: '%s'", salida[1]);

    printf("TC-LOG-02 (FR-LOG-02): %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
