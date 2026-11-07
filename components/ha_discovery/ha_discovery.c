/* L1 ha_discovery — Discovery de Home Assistant (FSD §10.2; FR-HA-02, FR-HA-03). Núcleo puro. */
#include "ha_discovery.h"
#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>

typedef struct { const char *medida, *nombre, *clase, *unidad; } had_def_t;

static const had_def_t DEF[HAD_N_MEDIDAS] = {
    {"temperatura", "Temperatura", "temperature", "°C"},
    {"humedad", "Humedad", "humidity", "%"},
    {"punto_rocio", "Punto de rocío", "temperature", "°C"},
};

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

/* Contenido de una cadena JSON (sin comillas) con escape de comillas, barra inversa y controles */
static void escapar(esc_t *e, const char *s)
{
    for (const unsigned char *p = (const unsigned char *)(s ? s : ""); *p && !e->roto; p++) {
        if (*p == '"' || *p == '\\') poner(e, "\\%c", *p);
        else if (*p < 0x20) poner(e, "\\u%04x", *p);
        else poner(e, "%c", *p);
    }
}

static void clave(esc_t *e, const char *k, const char *v)
{
    poner(e, "\"%s\":\"", k);
    escapar(e, v);
    poner(e, "\"");
}

static int fin(esc_t *e)
{
    if (e->roto) { if (e->cap) e->buf[0] = '\0'; return -1; }
    return (int)e->len;
}

int had_topico(char *buf, size_t cap, const char *nodo, had_medida_t m)
{
    esc_t e = {buf, cap, 0, cap == 0 || m >= HAD_N_MEDIDAS};
    if (!e.roto) poner(&e, HAD_PREFIJO "/sensor/%s/%s/config", nodo, DEF[m].medida);
    return fin(&e);
}

int had_config_json(char *buf, size_t cap, const char *sitio, const char *zona,
                    const char *nodo, const char *fw, had_medida_t m)
{
    esc_t e = {buf, cap, 0, cap == 0 || m >= HAD_N_MEDIDAS};
    if (e.roto) return fin(&e);
    const had_def_t *d = &DEF[m];
    poner(&e, "{");
    clave(&e, "name", d->nombre);
    poner(&e, ",\"unique_id\":\"");                       /* sin sitio ni zona (D23) */
    escapar(&e, nodo); poner(&e, "_%s\"", d->medida);
    poner(&e, ",\"state_topic\":\"");
    escapar(&e, sitio); poner(&e, "/"); escapar(&e, zona); poner(&e, "/"); escapar(&e, nodo);
    poner(&e, "/%s\"", d->medida);
    poner(&e, ",");
    clave(&e, "value_template", "{{ value_json.v }}");
    poner(&e, ",");
    clave(&e, "unit_of_measurement", d->unidad);
    poner(&e, ",");
    clave(&e, "device_class", d->clase);
    poner(&e, ",\"state_class\":\"measurement\",\"expire_after\":%d", HAD_EXPIRE_AFTER_S);
    poner(&e, ",\"availability_topic\":\"");
    escapar(&e, sitio); poner(&e, "/"); escapar(&e, zona); poner(&e, "/"); escapar(&e, nodo);
    poner(&e, "/status\"");
    poner(&e, ",\"availability_template\":\"{{ value_json.estado }}\"");
    poner(&e, ",\"payload_available\":\"online\",\"payload_not_available\":\"offline\"");
    poner(&e, ",\"device\":{\"identifiers\":[\"");
    escapar(&e, nodo);
    poner(&e, "\"],\"name\":\"Clima ");
    escapar(&e, sitio); poner(&e, " "); escapar(&e, zona);
    poner(&e, "\",");
    clave(&e, "model", HAD_MODELO);
    poner(&e, ",");
    clave(&e, "sw_version", fw);
    poner(&e, "}}");
    return fin(&e);
}
