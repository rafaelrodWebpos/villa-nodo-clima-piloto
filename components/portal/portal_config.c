/* L1 portal — registro de configuración de §17 (T05, FR-POR-06). Núcleo puro. */
#include "portal_config.h"
#include <stdio.h>
#include <string.h>

static int copia(char *dst, size_t cap, const char *src)
{
    size_t n = src ? strlen(src) : 0;
    if (n >= cap) return -1;                    /* nunca truncar */
    memcpy(dst, src ? src : "", n + 1);
    return 0;
}

int portal_config_desde(const char *const v[PORTAL_N_CAMPOS], portal_config_t *c)
{
    memset(c, 0, sizeof *c);
    c->version = PORTAL_CONFIG_VERSION;
    const char *p = v[PORTAL_MQTT_PORT];
    if (!p || !*p || strlen(p) > 5) return -1;
    unsigned long puerto = 0;
    for (; *p; p++) {
        if (*p < '0' || *p > '9') return -1;
        puerto = puerto * 10 + (unsigned long)(*p - '0');
    }
    if (puerto < 1 || puerto > 65535) return -1;
    c->mqtt_port = (uint16_t)puerto;
    if (copia(c->wifi_ssid, sizeof c->wifi_ssid, v[PORTAL_WIFI_SSID]) ||
        copia(c->wifi_pass, sizeof c->wifi_pass, v[PORTAL_WIFI_PASS]) ||
        copia(c->mqtt_host, sizeof c->mqtt_host, v[PORTAL_MQTT_HOST]) ||
        copia(c->mqtt_user, sizeof c->mqtt_user, v[PORTAL_MQTT_USER]) ||
        copia(c->mqtt_pass, sizeof c->mqtt_pass, v[PORTAL_MQTT_PASS]) ||
        copia(c->sitio, sizeof c->sitio, v[PORTAL_SITIO]) ||
        copia(c->zona, sizeof c->zona, v[PORTAL_ZONA]))
        return -1;
    return 0;
}

void portal_config_valores(const portal_config_t *c, char puerto[6], const char *v[PORTAL_N_CAMPOS])
{
    snprintf(puerto, 6, "%u", (unsigned)c->mqtt_port);
    v[PORTAL_WIFI_SSID] = c->wifi_ssid;
    v[PORTAL_WIFI_PASS] = c->wifi_pass;
    v[PORTAL_MQTT_HOST] = c->mqtt_host;
    v[PORTAL_MQTT_PORT] = puerto;
    v[PORTAL_MQTT_USER] = c->mqtt_user;
    v[PORTAL_MQTT_PASS] = c->mqtt_pass;
    v[PORTAL_SITIO] = c->sitio;
    v[PORTAL_ZONA] = c->zona;
}
