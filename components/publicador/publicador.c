/* L1 publicador — tópicos y payloads MQTT (FSD §9.2, §9.3; FR-MQTT-01, FR-MQTT-02,
 * FR-MQTT-08). Núcleo puro. */
#include "publicador.h"
#include <inttypes.h>
#include <stdarg.h>
#include <stdio.h>

static const char *const NOMBRE[PUB_N_MEDIDAS] = {"temperatura", "humedad", "punto_rocio"};
static const char *const UNIDAD[PUB_N_MEDIDAS] = {"°C", "%", "°C"};

const char *pub_nombre_medida(pub_medida_t m) { return m < PUB_N_MEDIDAS ? NOMBRE[m] : ""; }
const char *pub_unidad(pub_medida_t m) { return m < PUB_N_MEDIDAS ? UNIDAD[m] : ""; }

/* Escritor acotado: si algo no cabe, todo el resultado es -1 y el búfer queda vacío */
typedef struct { char *buf; size_t cap, len; bool roto; } esc_t;

static void poner(esc_t *e, const char *fmt, ...)
{
    if (e->roto) return;
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(e->buf + e->len, e->cap - e->len, fmt, ap);
    va_end(ap);
    if (n < 0 || (size_t)n >= e->cap - e->len) { e->roto = true; return; }
    e->len += (size_t)n;
}

/* Cadena JSON con escape de comillas, barra inversa y controles */
static void cadena(esc_t *e, const char *s)
{
    poner(e, "\"");
    for (const unsigned char *p = (const unsigned char *)(s ? s : ""); *p && !e->roto; p++) {
        if (*p == '"' || *p == '\\') poner(e, "\\%c", *p);
        else if (*p < 0x20) poner(e, "\\u%04x", *p);
        else poner(e, "%c", *p);
    }
    poner(e, "\"");
}

static int fin(esc_t *e)
{
    if (e->roto) { if (e->cap) e->buf[0] = '\0'; return -1; }
    return (int)e->len;
}

int pub_topico(char *buf, size_t cap, const char *sitio, const char *zona, const char *nodo, const char *sufijo)
{
    esc_t e = {buf, cap, 0, cap == 0};
    poner(&e, "%s/%s/%s/%s", sitio, zona, nodo, sufijo);
    return fin(&e);
}

int pub_medida_json(char *buf, size_t cap, pub_medida_t m, float v, bool ts_valido, int64_t ts)
{
    esc_t e = {buf, cap, 0, cap == 0};
    if (v == 0.0f) v = 0.0f;                     /* sin «-0.0» */
    poner(&e, "{\"v\":%.1f,\"u\":", (double)v);
    cadena(&e, pub_unidad(m));
    if (ts_valido) poner(&e, ",\"ts\":%" PRId64 "}", ts);
    else poner(&e, ",\"ts\":null}");
    return fin(&e);
}

int pub_status_json(char *buf, size_t cap, const pub_status_t *s)
{
    esc_t e = {buf, cap, 0, cap == 0};
    poner(&e, "{\"estado\":\"%s\",\"fw\":", s->online ? "online" : "offline");
    cadena(&e, s->fw);
    poner(&e, ",\"rssi\":%d,\"reset\":", s->rssi);
    cadena(&e, s->reset ? s->reset : "otro");
    poner(&e, ",\"uptime_s\":%" PRIu32 ",\"lecturas\":%" PRIu32 ",\"err_sensor\":%" PRIu32 ",\"ota\":",
          s->uptime_s, s->lecturas, s->err_sensor);
    cadena(&e, s->ota ? s->ota : "ninguno");
    poner(&e, ",\"hora_valida\":%s}", s->hora_valida ? "true" : "false");
    return fin(&e);
}
