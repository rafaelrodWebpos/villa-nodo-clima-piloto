/* TC-MED-03 · FR-MED-03, TC-MED-04 · FR-MED-04, TC-MED-05 · FR-MED-05 (host):
 * punto de rocío, «no publicar punto_rocio» y redondeo (FSD §5.3, §5.4), más
 * la línea E3 de §18 que escribe cada ciclo. argv[1] elige el test. */
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "medicion.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

/* Referencia en doble precisión, escrita aquí a partir de §5.4 */
static double td_ref(double t, double hr)
{
    double g = log(hr / 100.0) + (17.62 * t) / (243.12 + t);
    return 243.12 * g / (17.62 - g);
}

static void med03(void)
{
    /* 200 pares: rejilla de 20 T × 10 HR sobre T ∈ [−10, 50], HR ∈ [1, 100], extremos incluidos */
    int n = 0; double peor = 0;
    for (int i = 0; i < 20; i++) {
        for (int j = 0; j < 10; j++) {
            float t = (float)(-10.0 + 60.0 * i / 19.0), hr = (float)(1.0 + 99.0 * j / 9.0);
            med_lectura_t m = med_procesar(true, t, hr);
            n++;
            ESPERA(m.td_valida, "T=%.3f HR=%.3f: sin punto de rocío", t, hr);
            ESPERA(isfinite(m.td_crudo), "T=%.3f HR=%.3f: Td no finito", t, hr);
            double e = fabs(m.td_crudo - td_ref(t, hr));
            if (e > peor) peor = e;
            ESPERA(e <= 0.1, "T=%.3f HR=%.3f: |Td − ref| = %.4f", t, hr, e);
        }
    }
    ESPERA(n == 200, "pares = %d", n);
    printf("TC-MED-03: %s (%d pares, error máximo %.5f °C)\n", fallos ? "FALLO" : "ok", n, peor);
}

static void med04(void)
{
    med_lectura_t a = med_procesar(true, 21.0f, 0.0f);       /* HR = 0 */
    ESPERA(a.valida && !a.td_valida, "HR = 0: td_valida = %d", a.td_valida);
    med_lectura_t b = med_procesar(false, 0.0f, 0.0f);       /* T inválida (FR-SEN-02) */
    ESPERA(!b.valida && !b.td_valida, "lectura inválida: valida = %d, td_valida = %d", b.valida, b.td_valida);
    char l[MED_LINEA_MAX];
    med_linea(l, sizeof l, &a, NULL);
    ESPERA(strcmp(l, "med: T=21.0 HR=0.0 Td=-") == 0, "línea con HR = 0: '%s'", l);
    med_linea(l, sizeof l, &b, "crc");
    ESPERA(strcmp(l, "med: invalida (crc)") == 0, "línea inválida: '%s'", l);
    /* Prohibido: 0, NaN, −273 o el valor anterior en lugar de «no publicar» */
    med_lectura_t c = med_procesar(true, 21.0f, 50.0f);
    ESPERA(c.td_valida, "HR = 50: sin punto de rocío");
    med_lectura_t d = med_procesar(true, 21.0f, 0.0f);
    ESPERA(!d.td_valida, "HR = 0 tras una válida: td_valida = %d (valor anterior)", d.td_valida);
    printf("TC-MED-04: %s\n", fallos ? "FALLO" : "ok");
}

static void med05(void)
{
    const struct { float x; const char *s; } v[] = {
        {21.45f, "21.5"}, {-0.05f, "-0.1"}, {21.449f, "21.4"}, {99.96f, "100.0"},
        {-0.04f, "0.0"},   /* un cero negativo no se escribe como «-0.0» */
    };
    for (size_t i = 0; i < sizeof v / sizeof *v; i++) {
        char s[16];
        snprintf(s, sizeof s, "%.1f", med_redondear1(v[i].x));
        ESPERA(strcmp(s, v[i].s) == 0, "%.4f -> '%s', esperado '%s'", v[i].x, s, v[i].s);
    }
    /* La línea E3 usa los valores redondeados, con 1 decimal */
    med_lectura_t m = med_procesar(true, 21.45f, 99.96f);
    char l[MED_LINEA_MAX];
    med_linea(l, sizeof l, &m, NULL);
    char td[16]; snprintf(td, sizeof td, "%.1f", m.td);
    char esperada[64]; snprintf(esperada, sizeof esperada, "med: T=21.5 HR=100.0 Td=%s", td);
    ESPERA(strcmp(l, esperada) == 0, "línea '%s', esperada '%s'", l, esperada);
    ESPERA(m.t == med_redondear1(21.45f) && m.hr == med_redondear1(99.96f), "valores sin redondear");
    printf("TC-MED-05: %s\n", fallos ? "FALLO" : "ok");
}

int main(int argc, char **argv)
{
    const char *t = argc > 1 ? argv[1] : "";
    if (!strcmp(t, "med04")) med04(); else if (!strcmp(t, "med05")) med05(); else med03();
    return fallos != 0;
}
