/* L2 conectividad — seguridad mínima del STA (FSD FR-CON-07, SEC-07). Núcleo puro:
 * el adaptador traduce el resultado a wifi_config_t (threshold.authmode, pmf_cfg). */
#pragma once
#include <stdbool.h>

typedef enum {
    CON_STA_UMBRAL_ABIERTA,     /* wifi_pass vacía: red abierta (§17) */
    CON_STA_UMBRAL_WPA2_PSK,    /* con clave: nunca una red abierta ni WEP/WPA */
} con_sta_umbral_t;

typedef struct {
    con_sta_umbral_t umbral;    /* threshold.authmode mínimo */
    bool pmf_capaz;             /* pmf_cfg.capable */
    bool pmf_requerido;         /* pmf_cfg.required: no, dejaría fuera routers sin PMF */
} con_sta_seguridad_t;

con_sta_seguridad_t con_sta_seguridad(const char *wifi_pass);
