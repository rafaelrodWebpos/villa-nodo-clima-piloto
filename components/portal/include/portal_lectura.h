/* L2 portal — lectura del cuerpo de POST / (FR-POR-09, SEC-05, D25). Núcleo puro: decide,
 * por cada resultado de httpd_req_recv, si seguir, esperar otra vez o cortar. */
#pragma once

#define PORTAL_ESPERAS_MAX 3          /* D25: 3 esperas seguidas sin datos → 408 */

typedef enum {
    PORTAL_LECTURA_DATOS,     /* llegaron n > 0 bytes: sumar y seguir */
    PORTAL_LECTURA_ESPERAR,   /* una espera sin datos más, por debajo del límite */
    PORTAL_LECTURA_408,       /* tercera espera seguida: responder 408 y cerrar */
    PORTAL_LECTURA_CORTAR,    /* error de socket o cierre del cliente: cortar sin respuesta */
} portal_lectura_t;

/* n: lo que devolvió httpd_req_recv (> 0 bytes; es_timeout = 1 si fue
 * HTTPD_SOCK_ERR_TIMEOUT). *esperas cuenta las seguidas y vuelve a 0 con datos. */
portal_lectura_t portal_lectura_paso(int n, int es_timeout, int *esperas);
