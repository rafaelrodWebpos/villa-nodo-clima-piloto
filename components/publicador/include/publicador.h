/* L1 publicador — tópicos y payloads MQTT (FSD §9.2, §9.3): tópicos
 * <sitio>/<zona>/<nodo>/<medida|status> (FR-MQTT-01), payload de medida
 * (FR-MQTT-02) y `status` con los 9 campos de diagnóstico (FR-MQTT-08).
 * Núcleo puro, sin ESP-IDF; lo compila tests/host. Todas las funciones
 * devuelven la longitud escrita, o -1 si no cabe (el búfer queda vacío). */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum { PUB_TEMPERATURA, PUB_HUMEDAD, PUB_PUNTO_ROCIO, PUB_N_MEDIDAS } pub_medida_t;

const char *pub_nombre_medida(pub_medida_t m);   /* «temperatura», «humedad», «punto_rocio» */
const char *pub_unidad(pub_medida_t m);          /* «°C», «%», «°C» */

/* «<sitio>/<zona>/<nodo>/<sufijo>» */
int pub_topico(char *buf, size_t cap, const char *sitio, const char *zona, const char *nodo, const char *sufijo);

/* {"v":<v con 1 decimal>,"u":"<unidad>","ts":<entero|null>} */
int pub_medida_json(char *buf, size_t cap, pub_medida_t m, float v, bool ts_valido, int64_t ts);

typedef struct {
    bool online;            /* estado: online | offline */
    const char *fw;         /* versión de la aplicación */
    int rssi;               /* dBm */
    const char *reset;      /* valor de §9.3 (diag_reset_nombre) */
    uint32_t uptime_s;
    uint32_t lecturas;
    uint32_t err_sensor;
    const char *ota;        /* ninguno | en_curso | ok | rechazado:… | error:… */
    bool hora_valida;
} pub_status_t;

/* Diagnóstico de §9.3 en su orden: estado, fw, rssi, reset, uptime_s, lecturas, err_sensor, ota, hora_valida */
int pub_status_json(char *buf, size_t cap, const pub_status_t *s);

/* Last Will de `status` (§9.2) */
#define PUB_LWT_OFFLINE "{\"estado\":\"offline\"}"
