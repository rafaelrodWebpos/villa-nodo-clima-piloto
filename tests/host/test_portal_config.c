/* TC-POR-10 · FR-POR-06 (host): los datos del formulario se guardan tal cual.
 * Valores válidos -> registro -> valores: idénticos y siguen siendo válidos;
 * un valor que no cabe se rechaza (nunca se trunca). */
#include <stdio.h>
#include <string.h>
#include "portal_config.h"
#include "portal_validar.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

static char *rep(char ch, int n) { static char b[4][128]; static int k; char *p = b[k++ % 4]; memset(p, ch, (size_t)n); p[n] = 0; return p; }

int main(void)
{
    /* Los máximos de §17 en cada campo */
    const char *v[PORTAL_N_CAMPOS] = {
        [PORTAL_WIFI_SSID] = rep('s', 32), [PORTAL_WIFI_PASS] = rep('p', 63),
        [PORTAL_MQTT_HOST] = "broker-1.local", [PORTAL_MQTT_PORT] = "65535",
        [PORTAL_MQTT_USER] = rep('u', 64), [PORTAL_MQTT_PASS] = "",
        [PORTAL_SITIO] = "sitio_1-a", [PORTAL_ZONA] = "zona1",
    };
    portal_validacion_t r;
    portal_validar(v, &r);
    ESPERA(r.n_errores == 0, "los valores de partida no son válidos (%d)", r.n_errores);

    portal_config_t c;
    memset(&c, 0xA5, sizeof c);
    ESPERA(portal_config_desde(v, &c) == 0, "no se guardan valores válidos");
    ESPERA(c.version == PORTAL_CONFIG_VERSION, "versión %d", c.version);
    ESPERA(c.mqtt_port == 65535, "puerto %u", c.mqtt_port);

    char puerto[6];
    const char *w[PORTAL_N_CAMPOS];
    portal_config_valores(&c, puerto, w);
    for (int i = 0; i < PORTAL_N_CAMPOS; i++)
        ESPERA(w[i] && strcmp(w[i], v[i]) == 0, "%s cambia: '%.20s' -> '%.20s'", PORTAL_NAME[i], v[i], w[i] ? w[i] : "(null)");
    portal_validar(w, &r);
    ESPERA(r.n_errores == 0, "lo guardado ya no es válido (%d)", r.n_errores);

    /* Un valor que no cabe en el registro: -1 (nunca truncado) */
    const char *x[PORTAL_N_CAMPOS];
    memcpy(x, v, sizeof x);
    x[PORTAL_ZONA] = rep('z', 40);
    ESPERA(portal_config_desde(x, &c) == -1, "un valor demasiado largo se acepta");
    memcpy(x, v, sizeof x);
    x[PORTAL_MQTT_PORT] = "12a";
    ESPERA(portal_config_desde(x, &c) == -1, "un puerto no numérico se acepta");

    printf("TC-POR-10 (FR-POR-06): %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
