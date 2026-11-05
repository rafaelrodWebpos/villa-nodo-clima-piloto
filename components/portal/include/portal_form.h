/* L1 portal — generador del formulario de §17 (FR-POR-03). Núcleo puro:
 * compila sin ESP-IDF. Los textos visibles están en portal_textos.h. */
#pragma once
#include <stddef.h>

typedef enum {
    PORTAL_WIFI_SSID, PORTAL_WIFI_PASS,
    PORTAL_MQTT_HOST, PORTAL_MQTT_PORT, PORTAL_MQTT_USER, PORTAL_MQTT_PASS,
    PORTAL_SITIO, PORTAL_ZONA,
    PORTAL_N_CAMPOS
} portal_campo_t;

/* Atributo name de cada campo: el «Nombre» de §17. */
extern const char *const PORTAL_NAME[PORTAL_N_CAMPOS];

typedef struct {
    const char *id;                          /* identificador del nodo (§16) */
    const char *version;                     /* versión del firmware en ejecución */
    const char *valores[PORTAL_N_CAMPOS];    /* valores a conservar; NULL = por defecto.
                                                Los secretos se ignoran siempre. */
    const char *error[PORTAL_N_CAMPOS];      /* mensaje bajo el campo (FR-POR-04), o NULL.
                                                Con alguno, el aviso general va arriba. */
    const char *aviso;                       /* otro aviso arriba (p. ej., FR-POR-05), o NULL */
    const char *aviso_id;                    /* su marca (atributo id) */
} portal_form_t;

/* Escribe el HTML del formulario en buf (con NUL). Devuelve la longitud, o 0
 * si no cabe en cap. */
size_t portal_form_html(char *buf, size_t cap, const portal_form_t *f);

/* Página corta con un mensaje (pantallas de FR-POR-05/06 y la temporal de
 * envío válido). Misma cabecera y estilo que el formulario; sin campos. */
size_t portal_mensaje_html(char *buf, size_t cap, const char *id, const char *version, const char *mensaje,
                           const char *marca, int refresco_s);   /* marca = atributo id; refresco 0 = no */
