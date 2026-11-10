/* L2 portal — lectura del cuerpo de POST / (FR-POR-09, SEC-05). Núcleo puro. */
#include "portal_lectura.h"

portal_lectura_t portal_lectura_paso(int n, int es_timeout, int *esperas)
{
    if (es_timeout) return ++*esperas >= PORTAL_ESPERAS_MAX ? PORTAL_LECTURA_408 : PORTAL_LECTURA_ESPERAR;
    if (n <= 0) return PORTAL_LECTURA_CORTAR;
    *esperas = 0;
    return PORTAL_LECTURA_DATOS;
}
