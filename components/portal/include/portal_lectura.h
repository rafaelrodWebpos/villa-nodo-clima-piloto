/* L2 portal — lectura del cuerpo de POST / (FR-POR-09, SEC-05, D25). Núcleo puro: decide,
 * por cada resultado de httpd_req_recv, si seguir, esperar otra vez o cortar. */
#pragma once
#include <stdint.h>

#define PORTAL_ESPERAS_MAX 3          /* D25: 3 esperas seguidas sin datos → 408 */
/* D25: 20 s en total desde el inicio del cuerpo. Se corta en cuanto han pasado 15 s: la
 * lectura siguiente puede esperar hasta 5 s (recv_wait_timeout de esp_http_server), así que
 * el total nunca pasa de 20 s aunque el cliente mande 1 byte por espera (H-85). */
#define PORTAL_PLAZO_CORTE_MS 15000
#define PORTAL_PLAZO_TOTAL_MS 20000

typedef enum {
    PORTAL_LECTURA_DATOS,     /* llegaron n > 0 bytes dentro del plazo: sumar y seguir */
    PORTAL_LECTURA_ESPERAR,   /* una espera sin datos más, por debajo de los límites */
    PORTAL_LECTURA_408,       /* tercera espera seguida o plazo agotado: 408 y cerrar */
    PORTAL_LECTURA_CORTAR,    /* error de socket o cierre del cliente: cortar sin respuesta */
} portal_lectura_t;

/* n: lo que devolvió httpd_req_recv (> 0 bytes; es_timeout = 1 si fue
 * HTTPD_SOCK_ERR_TIMEOUT); transcurrido_ms: desde el inicio de la lectura del cuerpo;
 * completo = 1 si con estos n bytes el cuerpo ya está entero. *esperas cuenta las
 * seguidas y vuelve a 0 con datos. */
portal_lectura_t portal_lectura_paso(int n, int es_timeout, int64_t transcurrido_ms, int completo, int *esperas);
