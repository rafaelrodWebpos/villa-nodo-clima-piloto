/* L2 conectividad — tabla de transiciones (FSD §6.3). Núcleo puro.
 * Solo contiene las filas ya implementadas; para el resto devuelve fila NULL
 * («la tabla aún no lo trata»), que no es ni «ign» ni «imp» de §6.4. */
#include "conectividad.h"
#include <stddef.h>

static const char *const NOMBRE_ESTADO[CON_N_ESTADOS] = {
    "ARRANQUE", "PORTAL", "VALIDANDO", "CONECTANDO_WIFI",
    "CONECTANDO_BROKER", "OPERATIVO", "OTA_DESCARGA",
};
static const char *const NOMBRE_EVENTO[CON_N_EVENTOS] = {
    "fin_arranque",
};

con_transicion_t con_transicion(con_estado_t origen, con_evento_t evento, con_guardas_t g)
{
    if (origen == CON_ARRANQUE && evento == CON_EV_FIN_ARRANQUE) {
        return g.config_valida
            ? (con_transicion_t){"T01", CON_CONECTANDO_WIFI, CON_ACC_ARRANCAR_STA}
            : (con_transicion_t){"T02", CON_PORTAL, CON_ACC_ARRANCAR_PORTAL};
    }
    return (con_transicion_t){NULL, origen, CON_ACC_NINGUNA};
}

const char *con_nombre_estado(con_estado_t e)
{
    return (e >= 0 && e < CON_N_ESTADOS) ? NOMBRE_ESTADO[e] : "?";
}

const char *con_nombre_evento(con_evento_t ev)
{
    return (ev >= 0 && ev < CON_N_EVENTOS) ? NOMBRE_EVENTO[ev] : "?";
}
