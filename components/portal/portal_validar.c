/* L1 portal — validador de §17 (FR-POR-04; D11 para zona, D23 para sitio).
 * Núcleo puro. Las reglas son las de la columna «Validación» de §17; los
 * mensajes visibles están en portal_textos.h. */
#include "portal_validar.h"
#include "portal_textos.h"
#include <string.h>

static size_t largo(const char *s) { return s ? strlen(s) : 0; }

static int solo(const char *s, const char *permitidos)
{
    for (; *s; s++) if (!strchr(permitidos, *s)) return 0;
    return 1;
}

static int es_digitos(const char *s) { return *s && solo(s, "0123456789"); }

/* a.b.c.d con cada parte 0–255 y de 1 a 3 cifras */
static int ipv4(const char *s)
{
    int partes = 0;
    while (partes < 4) {
        int n = 0, cifras = 0;
        while (*s >= '0' && *s <= '9' && cifras < 4) { n = n * 10 + (*s++ - '0'); cifras++; }
        if (cifras == 0 || cifras > 3 || n > 255) return 0;
        partes++;
        if (partes < 4) { if (*s != '.') return 0; s++; }
    }
    return *s == '\0';
}

static int host_ok(const char *s)
{
    size_t n = largo(s);
    if (n < 1 || n > 63) return 0;
    if (!solo(s, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")) return 0;
    /* Solo cifras y puntos: tiene que ser una IPv4 decimal válida */
    if (solo(s, "0123456789.")) return ipv4(s);
    return 1;
}

static int puerto_ok(const char *s)
{
    if (!s || !es_digitos(s) || strlen(s) > 5) return 0;
    long n = 0;
    for (; *s; s++) n = n * 10 + (*s - '0');
    return n >= 1 && n <= 65535;
}

static int clave_wifi_ok(const char *s)
{
    size_t n = largo(s);
    if (n == 0) return 1;                       /* red abierta */
    if (n < 8 || n > 63) return 0;
    for (; *s; s++) if ((unsigned char)*s < 0x20 || (unsigned char)*s > 0x7e) return 0;
    return 1;
}

static int id_ok(const char *s)                 /* ^[a-z0-9_-]{1,32}$ */
{
    size_t n = largo(s);
    return n >= 1 && n <= 32 && solo(s, "abcdefghijklmnopqrstuvwxyz0123456789_-");
}

void portal_validar(const char *const v[PORTAL_N_CAMPOS], portal_validacion_t *out)
{
    memset(out, 0, sizeof *out);
    size_t ssid = largo(v[PORTAL_WIFI_SSID]);
    if (ssid < 1 || ssid > 32)               out->error[PORTAL_WIFI_SSID] = TX_ERR_WIFI_SSID;
    if (!clave_wifi_ok(v[PORTAL_WIFI_PASS])) out->error[PORTAL_WIFI_PASS] = TX_ERR_WIFI_PASS;
    if (!host_ok(v[PORTAL_MQTT_HOST]))       out->error[PORTAL_MQTT_HOST] = TX_ERR_MQTT_HOST;
    if (!puerto_ok(v[PORTAL_MQTT_PORT]))     out->error[PORTAL_MQTT_PORT] = TX_ERR_MQTT_PORT;
    if (largo(v[PORTAL_MQTT_USER]) > 64)     out->error[PORTAL_MQTT_USER] = TX_ERR_MQTT_USER;
    if (largo(v[PORTAL_MQTT_PASS]) > 64)     out->error[PORTAL_MQTT_PASS] = TX_ERR_MQTT_PASS;
    if (!id_ok(v[PORTAL_SITIO]))             out->error[PORTAL_SITIO] = TX_ERR_ID;
    if (!id_ok(v[PORTAL_ZONA]))              out->error[PORTAL_ZONA] = TX_ERR_ID;
    for (int i = 0; i < PORTAL_N_CAMPOS; i++) if (out->error[i]) out->n_errores++;
}
