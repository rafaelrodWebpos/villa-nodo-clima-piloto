/* L1 ha_discovery — configuración de Discovery de Home Assistant (FSD §10.2):
 * una por medida, en homeassistant/sensor/<nodo>/<medida>/config, con
 * unique_id = <nodo>_<medida> y sw_version = la versión en ejecución (FR-HA-02)
 * y expire_after = 180 s (FR-HA-03). Núcleo puro, sin ESP-IDF; lo compila
 * tests/host. Las funciones devuelven la longitud escrita, o -1 si no cabe
 * (el búfer queda vacío) o si la medida no existe. */
#pragma once
#include <stddef.h>

typedef enum { HAD_TEMPERATURA, HAD_HUMEDAD, HAD_PUNTO_ROCIO, HAD_N_MEDIDAS } had_medida_t;

#define HAD_PREFIJO "homeassistant"
#define HAD_EXPIRE_AFTER_S 180
#define HAD_MODELO "Waveshare ESP32-S3-DEV-KIT-N8R8 + SHT41"

/* «homeassistant/sensor/<nodo>/<medida>/config» */
int had_topico(char *buf, size_t cap, const char *nodo, had_medida_t m);

/* JSON de §10.2 con sus campos en el orden del FSD */
int had_config_json(char *buf, size_t cap, const char *sitio, const char *zona,
                    const char *nodo, const char *fw, had_medida_t m);
