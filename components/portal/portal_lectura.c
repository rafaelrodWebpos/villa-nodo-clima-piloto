/* L2 portal — lectura del cuerpo de POST / (FR-POR-09, SEC-05). Núcleo puro. */
#include "portal_lectura.h"

portal_lectura_t portal_lectura_paso(int n, int es_timeout, int64_t transcurrido_ms, int completo, int *esperas)
{
    if (!es_timeout && n <= 0) return PORTAL_LECTURA_CORTAR;
    if (!es_timeout && completo) { *esperas = 0; return PORTAL_LECTURA_DATOS; }   /* entero: nunca 408 */
    if (transcurrido_ms >= PORTAL_PLAZO_CORTE_MS) return PORTAL_LECTURA_408;      /* cliente lento */
    if (es_timeout) return ++*esperas >= PORTAL_ESPERAS_MAX ? PORTAL_LECTURA_408 : PORTAL_LECTURA_ESPERAR;
    *esperas = 0;
    return PORTAL_LECTURA_DATOS;
}
