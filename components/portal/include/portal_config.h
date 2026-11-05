/* L1 portal — la configuración de §17 tal como se guarda en la NVS (T05,
 * FR-POR-06, FR-CFG-01). Núcleo puro: copia entre los valores del formulario
 * y el registro guardado, sin truncar nunca. */
#pragma once
#include <stdint.h>
#include "portal_form.h"

#define PORTAL_CONFIG_VERSION 1

typedef struct {
    uint8_t  version;
    char     wifi_ssid[33];
    char     wifi_pass[64];
    char     mqtt_host[64];
    uint16_t mqtt_port;
    char     mqtt_user[65];
    char     mqtt_pass[65];
    char     sitio[33];
    char     zona[33];
} portal_config_t;

/* Llena c con los valores ya validados (portal_validar sin errores). Devuelve
 * 0, o -1 si algún valor no cabe o el puerto no es un número (nunca trunca). */
int portal_config_desde(const char *const v[PORTAL_N_CAMPOS], portal_config_t *c);

/* Deja en v punteros a los campos de c (el puerto, como texto en puerto[6]),
 * para volver a validarlos al leerlos de la NVS. */
void portal_config_valores(const portal_config_t *c, char puerto[6], const char *v[PORTAL_N_CAMPOS]);
