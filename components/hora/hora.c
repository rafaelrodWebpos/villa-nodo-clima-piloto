/* L2 hora (FSD §13). Ver hora.h. */
#include <string.h>
#include "hora.h"

bool hora_es_valida(bool sincronizado, int64_t reloj, int64_t build)
{
    return sincronizado && build >= 0 && reloj >= build;
}

/* Días desde 1970-01-01 de una fecha civil (algoritmo de H. Hinnant). */
static int64_t dias_civil(int64_t a, unsigned m, unsigned d)
{
    a -= m <= 2;
    const int64_t era = (a >= 0 ? a : a - 399) / 400;
    const unsigned yoe = (unsigned)(a - era * 400);
    const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + (int64_t)doe - 719468;
}

static int num(const char *s, int n)
{
    int v = 0;
    for (int i = 0; i < n; i++) {
        char c = s[i];
        if (c == ' ' && i == 0 && n == 2) continue;      /* «Nov  7»: día con espacio delante */
        if (c < '0' || c > '9') return -1;
        v = v * 10 + (c - '0');
    }
    return v;
}

int64_t hora_build_epoch(const char *fecha, const char *hora)
{
    static const char meses[] = "JanFebMarAprMayJunJulAugSepOctNovDec";
    if (!fecha || !hora || strlen(fecha) != 11 || strlen(hora) != 8) return -1;
    if (fecha[3] != ' ' || fecha[6] != ' ' || hora[2] != ':' || hora[5] != ':') return -1;
    int m = -1;
    for (int i = 0; i < 12; i++)
        if (memcmp(fecha, meses + 3 * i, 3) == 0) { m = i + 1; break; }
    int d = num(fecha + 4, 2), a = num(fecha + 7, 4);
    int hh = num(hora, 2), mm = num(hora + 3, 2), ss = num(hora + 6, 2);
    if (m < 0 || d < 1 || d > 31 || a < 1970 || hh < 0 || hh > 23 || mm < 0 || mm > 59 || ss < 0 || ss > 60) return -1;
    return dias_civil(a, (unsigned)m, (unsigned)d) * 86400 + hh * 3600 + mm * 60 + ss;
}

void hora_iniciar(hora_sntp_t *h)
{
    memset(h, 0, sizeof *h);
}

unsigned hora_tick(hora_sntp_t *h, int64_t ahora_ms)
{
    unsigned acc = HORA_NADA;
    if (h->intento && ahora_ms - h->inicio_ms >= HORA_INTENTO_MS) {
        acc |= HORA_FALLO;
        h->intento = false;
        if (h->sincronizado) {              /* FR-TIME-04: el fallo no invalida; la siguiente, en 1 h */
            h->ref_ms = ahora_ms;
            return acc;
        }
    }
    if (!h->intento) {
        if (h->sincronizado && ahora_ms - h->ref_ms < HORA_RESYNC_MS) return acc;
        h->intento = true;                  /* sin hora (FR-TIME-06) o toca resincronizar (FR-TIME-04) */
        h->inicio_ms = ahora_ms;
    }
    return acc | HORA_PEDIR;                /* dentro de un intento, una petición por tick */
}

void hora_sincronizada(hora_sntp_t *h, int64_t ahora_ms)
{
    h->sincronizado = true;
    h->intento = false;
    h->ref_ms = ahora_ms;
}
