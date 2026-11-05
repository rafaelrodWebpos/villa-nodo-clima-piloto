/* L1 portal — generador del formulario de §17 (FR-POR-03). Núcleo puro.
 * HTML liviano, sin recursos externos, apto para teléfono (diseño H-36).
 * Los textos visibles salen todos de portal_textos.h. */
#include "portal_form.h"
#include "portal_textos.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

const char *const PORTAL_NAME[PORTAL_N_CAMPOS] = {
    [PORTAL_WIFI_SSID] = "wifi_ssid", [PORTAL_WIFI_PASS] = "wifi_pass",
    [PORTAL_MQTT_HOST] = "mqtt_host", [PORTAL_MQTT_PORT] = "mqtt_port",
    [PORTAL_MQTT_USER] = "mqtt_user", [PORTAL_MQTT_PASS] = "mqtt_pass",
    [PORTAL_SITIO] = "sitio",         [PORTAL_ZONA] = "zona",
};

typedef struct { char *buf; size_t cap, len; int lleno; } sal_t;

static void put(sal_t *s, const char *fmt, ...)
{
    if (s->lleno) return;
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(s->buf + s->len, s->cap - s->len, fmt, ap);
    va_end(ap);
    if (n < 0 || (size_t)n >= s->cap - s->len) { s->lleno = 1; return; }
    s->len += (size_t)n;
}

static void put_escapado(sal_t *s, const char *v)
{
    for (; v && *v; v++) {
        switch (*v) {
        case '&':  put(s, "&amp;");  break;
        case '<':  put(s, "&lt;");   break;
        case '>':  put(s, "&gt;");   break;
        case '"':  put(s, "&quot;"); break;
        case '\'': put(s, "&#39;");  break;
        default:   put(s, "%c", *v); break;
        }
    }
}

typedef struct {
    portal_campo_t campo;
    const char *etiqueta, *tipo, *ejemplo, *extra;
    int secreto;
    const char *ayuda;          /* texto pequeño bajo el campo, o NULL */
} def_campo_t;

/* Orden y atributos de cada campo. Las longitudes son las de §17; la
 * validación que cuenta la hace el nodo (FR-POR-04), no el navegador. */
static const def_campo_t WIFI[] = {
    {PORTAL_WIFI_SSID, TX_RED,   "text",     TX_EJ_RED, "maxlength=\"32\" required autocapitalize=\"none\" autocorrect=\"off\" spellcheck=\"false\"", 0, NULL},
    {PORTAL_WIFI_PASS, TX_CLAVE, "password", NULL, "maxlength=\"63\" autocomplete=\"off\"", 1, NULL},
};
static const def_campo_t MQTT[] = {
    {PORTAL_MQTT_HOST, TX_SERVIDOR, "text",     TX_EJ_SERVIDOR, "maxlength=\"63\" required autocapitalize=\"none\" autocorrect=\"off\" spellcheck=\"false\"", 0, NULL},
    {PORTAL_MQTT_PORT, TX_PUERTO,   "number",   NULL,           "min=\"1\" max=\"65535\" required", 0, NULL},
    {PORTAL_MQTT_USER, TX_USUARIO_OPC, "text",     NULL,           "maxlength=\"64\" autocapitalize=\"none\" autocorrect=\"off\" spellcheck=\"false\"", 0, NULL},
    {PORTAL_MQTT_PASS, TX_CLAVE_OPC,   "password", NULL,           "maxlength=\"64\" autocomplete=\"off\"", 1, NULL},
};
static const def_campo_t UBICACION[] = {
    {PORTAL_SITIO, TX_SITIO, "text", TX_EJ_SITIO, "maxlength=\"32\" required autocapitalize=\"none\" autocorrect=\"off\" spellcheck=\"false\"", 0, TX_AYUDA_ID},
    {PORTAL_ZONA,  TX_ZONA,  "text", TX_EJ_ZONA,  "maxlength=\"32\" required autocapitalize=\"none\" autocorrect=\"off\" spellcheck=\"false\"", 0, TX_AYUDA_ID},
};

static void campo(sal_t *s, const def_campo_t *d, const portal_form_t *f)
{
    const char *n = PORTAL_NAME[d->campo];
    put(s, "<label for=\"%s\">%s</label>", n, d->etiqueta);
    if (d->secreto) put(s, "<div class=\"ojo\">");
    put(s, "<input id=\"%s\" name=\"%s\" type=\"%s\" %s", n, n, d->tipo, d->extra);
    if (f->error[d->campo]) put(s, " aria-invalid=\"true\" aria-describedby=\"err-%s\"", n);
    if (d->ejemplo) put(s, " placeholder=\"%s\"", d->ejemplo);
    /* Los secretos nunca vuelven rellenos (FR-POR-03, «No debe ocurrir») */
    const char *v = d->secreto ? NULL : f->valores[d->campo];
    if (!v && d->campo == PORTAL_MQTT_PORT) v = "1883";       /* §17: por defecto */
    if (v) { put(s, " value=\""); put_escapado(s, v); put(s, "\""); }
    put(s, ">");
    if (d->secreto)
        put(s, "<button type=\"button\" aria-label=\"%s\" title=\"%s\" onclick=\"o('%s')\">&#128065;</button></div>",
            TX_MOSTRAR_CLAVE, TX_MOSTRAR_CLAVE, n);
    if (d->ayuda) put(s, "<small class=\"ayuda\">%s</small>", d->ayuda);
    /* FR-POR-04: el error del campo, debajo de él; el test lo busca por id=err-<name> */
    if (f->error[d->campo]) put(s, "<small class=\"error\" id=\"err-%s\">%s</small>", n, f->error[d->campo]);
}

static void bloque(sal_t *s, const char *titulo, const def_campo_t *d, size_t n, const portal_form_t *f)
{
    put(s, "<fieldset><legend>%s</legend>", titulo);
    for (size_t i = 0; i < n; i++) campo(s, &d[i], f);
    put(s, "</fieldset>");
}

static void cabecera(sal_t *s0, const char *id, const char *version, int refresco_s)
{
    sal_t *sp = s0;
    put(sp,
        "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        );
    if (refresco_s > 0) put(sp, "<meta http-equiv=\"refresh\" content=\"%d;url=/\">", refresco_s);
    put(sp,
        "<title>%s</title><style>"
        "body{font-family:system-ui,sans-serif;margin:0;padding:16px;max-width:28rem;margin-inline:auto;background:#f6f7f9;color:#1d2330}"
        "h1{font-size:1.4rem;margin:0}.sub{color:#5b6475;margin:.2rem 0 1rem;font-size:.9rem}"
        "fieldset{border:1px solid #d5d9e0;border-radius:10px;background:#fff;margin:0 0 1rem;padding:.6rem 1rem 1rem}"
        ".ayuda{display:block;color:#6b7280;font-size:.8rem;margin-top:.25rem}"
        ".error{display:block;color:#b42318;font-size:.85rem;margin-top:.25rem}"
        "input[aria-invalid]{border-color:#b42318}"
        ".aviso{background:#fef3f2;border:1px solid #fda29b;color:#912018;border-radius:10px;padding:.7rem 1rem;margin:0 0 1rem}"
        "legend{font-weight:600;padding:0 .3rem}label{display:block;margin:.7rem 0 .25rem;font-size:.95rem}"
        "input{box-sizing:border-box;width:100%%;font-size:1rem;padding:.6rem;border:1px solid #b9c0cc;border-radius:8px}"
        ".ojo{display:flex;gap:.4rem}.ojo button{flex:none;width:3rem;font-size:1.2rem;border:1px solid #b9c0cc;border-radius:8px;background:#fff}"
        "button[type=submit]{width:100%%;font-size:1.05rem;padding:.8rem;border:0;border-radius:10px;background:#1f6feb;color:#fff}"
        "</style></head><body>",
        TX_TITULO);
    put(sp, "<h1>%s</h1><p class=\"sub\">", TX_TITULO);
    put_escapado(sp, id);
    put(sp, " &middot; %s ", TX_FIRMWARE);
    put_escapado(sp, version);
}

size_t portal_form_html(char *buf, size_t cap, const portal_form_t *f)
{
    sal_t s = {buf, cap, 0, 0};
    if (!buf || cap == 0) return 0;
    buf[0] = 0;
    cabecera(&s, f->id, f->version, 0);
    put(&s, "</p>");
    int hay_errores = 0;
    for (int i = 0; i < PORTAL_N_CAMPOS; i++) if (f->error[i]) hay_errores = 1;
    if (hay_errores) put(&s, "<p class=\"aviso\" id=\"errores\" role=\"alert\">%s</p>", TX_AVISO_ERRORES);
    else if (f->aviso) put(&s, "<p class=\"aviso\" id=\"%s\" role=\"alert\">%s</p>", f->aviso_id ? f->aviso_id : "aviso", f->aviso);
    put(&s, "<form method=\"post\" action=\"/\">");
    bloque(&s, TX_BLOQUE_WIFI, WIFI, sizeof WIFI / sizeof *WIFI, f);
    bloque(&s, TX_BLOQUE_MQTT, MQTT, sizeof MQTT / sizeof *MQTT, f);
    bloque(&s, TX_BLOQUE_UBICACION, UBICACION, sizeof UBICACION / sizeof *UBICACION, f);
    put(&s, "<button type=\"submit\">%s</button></form>", TX_GUARDAR);
    put(&s, "<script>function o(i){var e=document.getElementById(i);e.type=e.type==='password'?'text':'password'}</script>"
            "</body></html>");
    if (s.lleno) { buf[0] = 0; return 0; }
    return s.len;
}

size_t portal_mensaje_html(char *buf, size_t cap, const char *id, const char *version, const char *mensaje,
                           const char *marca, int refresco_s)
{
    sal_t s = {buf, cap, 0, 0};
    if (!buf || cap == 0) return 0;
    buf[0] = 0;
    cabecera(&s, id, version, refresco_s);
    put(&s, "</p><p class=\"mensaje\" id=\"%s\" role=\"status\">%s</p></body></html>", marca ? marca : "mensaje", mensaje);
    if (s.lleno) { buf[0] = 0; return 0; }
    return s.len;
}
