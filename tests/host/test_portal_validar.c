/* TC-POR-03 · FR-POR-04 (host): el validador de §17 con cada caso límite
 * (longitud 0, máximo, máximo + 1; sitio y zona con / + # mayúsculas o espacio).
 * Un rechazo nombra el campo: el error está en su posición y solo en ella. */
#include <stdio.h>
#include <string.h>
#include "portal_validar.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

static const char *BASE[PORTAL_N_CAMPOS] = {
    [PORTAL_WIFI_SSID] = "red-de-prueba", [PORTAL_WIFI_PASS] = "clave-de-prueba",
    [PORTAL_MQTT_HOST] = "broker.local",  [PORTAL_MQTT_PORT] = "1883",
    [PORTAL_MQTT_USER] = "",              [PORTAL_MQTT_PASS] = "",
    [PORTAL_SITIO] = "sitio1",            [PORTAL_ZONA] = "zona1",
};

static char *rep(char c, int n) { static char b[8][128]; static int k; char *p = b[k++ % 8]; memset(p, c, (size_t)n); p[n] = 0; return p; }

/* Valida BASE con el campo c cambiado a val; comprueba válido/inválido y que
 * solo ese campo lleva error. */
static void caso(portal_campo_t c, const char *val, int valido, int linea)
{
    const char *v[PORTAL_N_CAMPOS];
    memcpy(v, BASE, sizeof v);
    v[c] = val;
    portal_validacion_t r;
    portal_validar(v, &r);
    if (valido) {
        if (r.n_errores != 0 || r.error[c]) { fallos++; printf("FALLO línea %d: %s='%.20s' rechazado\n", linea, PORTAL_NAME[c], val ? val : "(null)"); }
    } else {
        int otros = 0;
        for (int i = 0; i < PORTAL_N_CAMPOS; i++) if (i != (int)c && r.error[i]) otros++;
        if (!r.error[c] || r.n_errores != 1 || otros) { fallos++; printf("FALLO línea %d: %s='%.20s' aceptado o mal nombrado (n=%d)\n", linea, PORTAL_NAME[c], val ? val : "(null)", r.n_errores); }
    }
}
#define OK(c, v)  caso(c, v, 1, __LINE__)
#define MAL(c, v) caso(c, v, 0, __LINE__)

int main(void)
{
    portal_validacion_t r;
    portal_validar(BASE, &r);
    ESPERA(r.n_errores == 0, "la base válida tiene %d errores", r.n_errores);

    /* wifi_ssid: 1–32 bytes */
    MAL(PORTAL_WIFI_SSID, ""); MAL(PORTAL_WIFI_SSID, NULL);
    OK(PORTAL_WIFI_SSID, "a"); OK(PORTAL_WIFI_SSID, rep('s', 32)); MAL(PORTAL_WIFI_SSID, rep('s', 33));
    /* wifi_pass: vacío (red abierta) u 8–63 ASCII imprimible */
    OK(PORTAL_WIFI_PASS, ""); MAL(PORTAL_WIFI_PASS, rep('p', 7)); OK(PORTAL_WIFI_PASS, rep('p', 8));
    OK(PORTAL_WIFI_PASS, rep('p', 63)); MAL(PORTAL_WIFI_PASS, rep('p', 64));
    MAL(PORTAL_WIFI_PASS, "clave\tcon-tab"); MAL(PORTAL_WIFI_PASS, "contraseña1");
    /* mqtt_host: 1–63 caracteres [A-Za-z0-9.-], nombre de host o IPv4 decimal */
    MAL(PORTAL_MQTT_HOST, ""); OK(PORTAL_MQTT_HOST, "h"); OK(PORTAL_MQTT_HOST, rep('h', 63)); MAL(PORTAL_MQTT_HOST, rep('h', 64));
    OK(PORTAL_MQTT_HOST, "Broker-1.local"); OK(PORTAL_MQTT_HOST, "10.0.0.5");
    MAL(PORTAL_MQTT_HOST, "broker local"); MAL(PORTAL_MQTT_HOST, "broker_1"); MAL(PORTAL_MQTT_HOST, "mqtt://broker");
    MAL(PORTAL_MQTT_HOST, "10.0.0.256"); MAL(PORTAL_MQTT_HOST, "10.0.0"); MAL(PORTAL_MQTT_HOST, "10..0.5");
    /* mqtt_port: 1–65535 */
    MAL(PORTAL_MQTT_PORT, ""); MAL(PORTAL_MQTT_PORT, "0"); OK(PORTAL_MQTT_PORT, "1"); OK(PORTAL_MQTT_PORT, "65535");
    MAL(PORTAL_MQTT_PORT, "65536"); MAL(PORTAL_MQTT_PORT, "18a3"); MAL(PORTAL_MQTT_PORT, "-1"); MAL(PORTAL_MQTT_PORT, "1883 ");
    /* mqtt_user, mqtt_pass: 0–64 bytes */
    OK(PORTAL_MQTT_USER, ""); OK(PORTAL_MQTT_USER, rep('u', 64)); MAL(PORTAL_MQTT_USER, rep('u', 65));
    OK(PORTAL_MQTT_PASS, ""); OK(PORTAL_MQTT_PASS, rep('k', 64)); MAL(PORTAL_MQTT_PASS, rep('k', 65));
    /* sitio y zona: ^[a-z0-9_-]{1,32}$ */
    portal_campo_t ids[] = {PORTAL_SITIO, PORTAL_ZONA};
    for (int i = 0; i < 2; i++) {
        portal_campo_t c = ids[i];
        MAL(c, ""); OK(c, "a"); OK(c, rep('z', 32)); MAL(c, rep('z', 33));
        OK(c, "planta_1-norte"); OK(c, "0");
        MAL(c, "a/b"); MAL(c, "a+b"); MAL(c, "a#b"); MAL(c, "Zona1"); MAL(c, "zona 1");
    }

    /* Varios campos mal a la vez: cada uno nombrado */
    const char *v[PORTAL_N_CAMPOS];
    memcpy(v, BASE, sizeof v);
    v[PORTAL_ZONA] = "Zona#1"; v[PORTAL_MQTT_PORT] = "0";
    portal_validar(v, &r);
    ESPERA(r.n_errores == 2 && r.error[PORTAL_ZONA] && r.error[PORTAL_MQTT_PORT], "dos errores: n=%d", r.n_errores);

    printf("TC-POR-03 (FR-POR-04): %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
