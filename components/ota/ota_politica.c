/* L2 ota — política de los comandos OTA (FSD §7, §12). Núcleo puro. */
#include "ota_politica.h"
#include <ctype.h>
#include <stdlib.h>
#include <string.h>

static const char *const TEXTO[] = {
    "ok", "rechazado:payload", "rechazado:host", "rechazado:ruta", "rechazado:misma_version",
    "rechazado:version_anterior", "rechazado:ocupado", "error:redirecciones", "error:tls",
    "error:imagen", "error:http", "error:red",
};

const char *ota_motivo_texto(ota_motivo_t m)
{
    return (m >= 0 && (size_t)m < sizeof TEXTO / sizeof TEXTO[0]) ? TEXTO[m] : "?";
}

/* ── FR-OTA-09: payload ─────────────────────────────────────────────────── */

static const char *saltar_blancos(const char *p, const char *fin)
{
    while (p < fin && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) p++;
    return p;
}

/* Cadena JSON desde p (en la comilla). Escapes admitidos: \" \\ \/; cualquier otro (o un
 * control) la invalida. Devuelve el puntero tras la comilla de cierre o NULL. */
static const char *leer_cadena(const char *p, const char *fin, char *out, size_t cap, size_t *n)
{
    if (p >= fin || *p != '"') return NULL;
    *n = 0;
    for (p++; p < fin; p++) {
        char c = *p;
        if (c == '"') { if (out) out[*n] = '\0'; return p + 1; }
        if ((unsigned char)c < 0x20) return NULL;
        if (c == '\\') {
            if (++p >= fin) return NULL;
            if (*p == '"' || *p == '\\' || *p == '/') c = *p;
            else return NULL;
        }
        if (out) { if (*n + 1 >= cap) return NULL; out[*n] = c; }
        (*n)++;
    }
    return NULL;
}

ota_motivo_t ota_payload(const char *json, size_t len, char *url, size_t cap)
{
    if (!json || !url || cap < OTA_URL_MAX + 1) return OTA_RECHAZADO_PAYLOAD;
    const char *p = json, *fin = json + len;
    char clave[8];
    size_t n;
    p = saltar_blancos(p, fin);
    if (p >= fin || *p++ != '{') return OTA_RECHAZADO_PAYLOAD;
    p = saltar_blancos(p, fin);
    if (!(p = leer_cadena(p, fin, clave, sizeof clave, &n)) || strcmp(clave, "url") != 0) return OTA_RECHAZADO_PAYLOAD;
    p = saltar_blancos(p, fin);
    if (p >= fin || *p++ != ':') return OTA_RECHAZADO_PAYLOAD;
    p = saltar_blancos(p, fin);
    if (!(p = leer_cadena(p, fin, url, cap, &n)) || n < 1 || n > OTA_URL_MAX) { url[0] = '\0'; return OTA_RECHAZADO_PAYLOAD; }
    p = saltar_blancos(p, fin);
    if (p >= fin || *p++ != '}') { url[0] = '\0'; return OTA_RECHAZADO_PAYLOAD; }   /* otra clave: «,» */
    p = saltar_blancos(p, fin);
    if (p != fin) { url[0] = '\0'; return OTA_RECHAZADO_PAYLOAD; }
    return OTA_OK;
}

/* ── FR-OTA-14 + FR-OTA-02: análisis estricto ───────────────────────────── */

static const char *const HOSTS[] = {"github.com", "release-assets.githubusercontent.com"};   /* D14 */
static const char RUTA_REPO[] = "/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/"; /* D19 */
static const char PRUEBA[] = "ota-test-";

typedef struct { char host[254]; const char *ruta; size_t ruta_len; } url_t;

/* Esquema exacto «https», autoridad sin usuario@ ni %, puerto ausente o 443, host de
 * [a-z0-9.-] (sin distinguir mayúsculas). Ruta: empieza por /, sin %, sin \, sin
 * segmentos . o .., sin controles; la consulta (tras ?) puede llevar % (GitHub firma así
 * sus enlaces de release-assets). Sin fragmento. */
static ota_motivo_t analizar(const char *s, url_t *u)
{
    if (!s) return OTA_RECHAZADO_HOST;
    const char *sep = strstr(s, "://");
    const char *inicio_ruta = sep ? strchr(sep + 3, '/') : NULL;
    for (const char *q = s; *q; q++)          /* controles, espacio, no ASCII, \ y # */
        if ((unsigned char)*q <= 0x20 || (unsigned char)*q >= 0x7f || *q == '\\' || *q == '#')
            return (inicio_ruta && q > inicio_ruta) ? OTA_RECHAZADO_RUTA : OTA_RECHAZADO_HOST;
    if (strncmp(s, "https://", 8) != 0) return OTA_RECHAZADO_HOST;          /* esquema exacto, en minúsculas */
    const char *a = s + 8, *barra = strchr(a, '/');
    if (!barra) return OTA_RECHAZADO_HOST;
    size_t alen = (size_t)(barra - a);
    if (alen == 0 || memchr(a, '@', alen) || memchr(a, '%', alen)) return OTA_RECHAZADO_HOST;
    const char *dos = memchr(a, ':', alen);
    size_t hlen = dos ? (size_t)(dos - a) : alen;
    if (dos && !(alen - hlen == 4 && strncmp(dos, ":443", 4) == 0)) return OTA_RECHAZADO_HOST;
    if (hlen == 0 || hlen >= sizeof u->host) return OTA_RECHAZADO_HOST;
    for (size_t i = 0; i < hlen; i++) {
        char c = (char)tolower((unsigned char)a[i]);
        if (!(isalnum((unsigned char)c) || c == '.' || c == '-')) return OTA_RECHAZADO_HOST;
        u->host[i] = c;
    }
    u->host[hlen] = '\0';
    const char *consulta = strchr(barra, '?');
    size_t rlen = consulta ? (size_t)(consulta - barra) : strlen(barra);
    if (memchr(barra, '%', rlen)) return OTA_RECHAZADO_RUTA;
    for (const char *seg = barra; seg < barra + rlen;) {                     /* segmentos . y .. */
        const char *sig = memchr(seg + 1, '/', (size_t)(barra + rlen - seg - 1));
        size_t sl = (size_t)((sig ? sig : barra + rlen) - seg - 1);
        if ((sl == 1 && seg[1] == '.') || (sl == 2 && seg[1] == '.' && seg[2] == '.')) return OTA_RECHAZADO_RUTA;
        if (!sig) break;
        seg = sig;
    }
    u->ruta = barra;
    u->ruta_len = rlen;
    return OTA_OK;
}

static bool host_permitido(const char *h)
{
    for (size_t i = 0; i < sizeof HOSTS / sizeof HOSTS[0]; i++)
        if (strcmp(h, HOSTS[i]) == 0) return true;
    return false;
}

ota_motivo_t ota_url_inicial(const char *url, bool imagen_banco, bool *es_prueba)
{
    if (es_prueba) *es_prueba = false;
    url_t u;
    ota_motivo_t m = analizar(url, &u);
    if (m != OTA_OK) return m;
    if (!host_permitido(u.host)) return OTA_RECHAZADO_HOST;                  /* FR-OTA-02 */
    const size_t pl = sizeof RUTA_REPO - 1;                                  /* FR-OTA-11 */
    if (strcmp(u.host, "github.com") != 0 || u.ruta_len <= pl || strncmp(u.ruta, RUTA_REPO, pl) != 0)
        return OTA_RECHAZADO_RUTA;
    const char *tag = u.ruta + pl;
    const bool prueba = strncmp(tag, PRUEBA, sizeof PRUEBA - 1) == 0;
    if (prueba && !imagen_banco) return OTA_RECHAZADO_RUTA;                  /* FR-OTA-13 */
    if (es_prueba) *es_prueba = prueba;
    return OTA_OK;
}

ota_motivo_t ota_url_redireccion(const char *url, int saltos)
{
    if (saltos > OTA_REDIRECCIONES_MAX) return OTA_ERROR_REDIRECCIONES;
    url_t u;
    ota_motivo_t m = analizar(url, &u);
    if (m == OTA_RECHAZADO_RUTA) return OTA_RECHAZADO_HOST;    /* T20: un salto malo es rechazado:host */
    if (m != OTA_OK) return m;
    return host_permitido(u.host) ? OTA_OK : OTA_RECHAZADO_HOST;
}

/* ── FR-OTA-05: versión ─────────────────────────────────────────────────── */

typedef struct { long n[3]; const char *pre; size_t pre_len; } semver_t;

static bool num_semver(const char **p, long *v)
{
    const char *s = *p;
    if (!isdigit((unsigned char)*s) || (*s == '0' && isdigit((unsigned char)s[1]))) return false;
    char *e;
    *v = strtol(s, &e, 10);
    if (*v < 0 || e - s > 9) return false;
    *p = e;
    return true;
}

/* MAJOR.MINOR.PATCH[-pre][+build], con una «v» inicial opcional */
static bool semver(const char *s, semver_t *v)
{
    if (!s) return false;
    if (*s == 'v') s++;
    for (int i = 0; i < 3; i++) {
        if (!num_semver(&s, &v->n[i])) return false;
        if (i < 2 && *s++ != '.') return false;
    }
    v->pre = NULL; v->pre_len = 0;
    if (*s == '-') {
        v->pre = ++s;
        while (*s && *s != '+') {
            if (!(isalnum((unsigned char)*s) || *s == '.' || *s == '-')) return false;
            s++;
        }
        v->pre_len = (size_t)(s - v->pre);
        if (v->pre_len == 0) return false;
    }
    if (*s == '+') { s++; if (!*s) return false; while (*s) s++; }
    return *s == '\0';
}

static int cmp_pre(const semver_t *a, const semver_t *b)
{
    if (!a->pre && !b->pre) return 0;
    if (!a->pre) return 1;                 /* sin pre-release va después */
    if (!b->pre) return -1;
    const char *x = a->pre, *xf = a->pre + a->pre_len, *y = b->pre, *yf = b->pre + b->pre_len;
    while (x < xf && y < yf) {
        const char *xe = memchr(x, '.', (size_t)(xf - x)), *ye = memchr(y, '.', (size_t)(yf - y));
        if (!xe) xe = xf;
        if (!ye) ye = yf;
        size_t xl = (size_t)(xe - x), yl = (size_t)(ye - y);
        bool xn = true, yn = true;
        for (size_t i = 0; i < xl; i++) xn &= isdigit((unsigned char)x[i]) != 0;
        for (size_t i = 0; i < yl; i++) yn &= isdigit((unsigned char)y[i]) != 0;
        int c;
        if (xn && yn) c = xl != yl ? (xl < yl ? -1 : 1) : memcmp(x, y, xl);
        else if (xn != yn) c = xn ? -1 : 1;
        else { c = memcmp(x, y, xl < yl ? xl : yl); if (!c && xl != yl) c = xl < yl ? -1 : 1; }
        if (c) return c < 0 ? -1 : 1;
        x = xe < xf ? xe + 1 : xf;
        y = ye < yf ? ye + 1 : yf;
    }
    return (x < xf) - (y < yf);
}

static int cmp_semver(const semver_t *a, const semver_t *b)
{
    for (int i = 0; i < 3; i++)
        if (a->n[i] != b->n[i]) return a->n[i] < b->n[i] ? -1 : 1;
    return cmp_pre(a, b);
}

ota_motivo_t ota_version(const char *en_ejecucion, const char *destino, bool es_prueba)
{
    semver_t d, e;
    if (!semver(destino, &d)) return OTA_ERROR_IMAGEN;
    if (en_ejecucion && strcmp(en_ejecucion, destino) == 0) return OTA_RECHAZADO_MISMA_VERSION;
    if (es_prueba) return OTA_OK;                                 /* ota-test-*: sin anti-downgrade (H-84) */
    if (!semver(en_ejecucion, &e)) return OTA_OK;                 /* versión propia ilegible: no bloquea */
    int c = cmp_semver(&d, &e);
    if (c == 0) return OTA_RECHAZADO_MISMA_VERSION;
    return c < 0 ? OTA_RECHAZADO_VERSION_ANTERIOR : OTA_OK;
}

/* ── FR-OTA-12: clasificación de fallos ─────────────────────────────────── */

ota_motivo_t ota_clasificar_fallo(ota_fallo_t fallo, int estado_http)
{
    switch (fallo) {
    case OTA_FALLO_DNS:
    case OTA_FALLO_TCP:
    case OTA_FALLO_TIMEOUT: return OTA_ERROR_RED;
    case OTA_FALLO_TLS:     return OTA_ERROR_TLS;
    case OTA_FALLO_HTTP:    return (estado_http >= 200 && estado_http < 300) ? OTA_OK : OTA_ERROR_HTTP;
    }
    return OTA_ERROR_RED;
}
