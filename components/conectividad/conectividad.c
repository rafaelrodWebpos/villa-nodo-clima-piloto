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
    "fin_arranque", "envío", "wifi_up", "wifi_down",
};

con_transicion_t con_transicion(con_estado_t origen, con_evento_t evento, con_guardas_t g)
{
    if (origen == CON_ARRANQUE && evento == CON_EV_FIN_ARRANQUE) {
        return g.config_valida
            ? (con_transicion_t){"T01", CON_CONECTANDO_WIFI, CON_ACC_ARRANCAR_STA}
            : (con_transicion_t){"T02", CON_PORTAL, CON_ACC_ARRANCAR_PORTAL};
    }
    if (origen == CON_PORTAL && evento == CON_EV_ENVIO) {
        return g.envio_valido
            ? (con_transicion_t){"T04", CON_VALIDANDO, CON_ACC_PROBAR_UNION}
            : (con_transicion_t){"T03", CON_PORTAL, CON_ACC_RESPONDER_ERRORES};
    }
    if (origen == CON_VALIDANDO) {
        switch (evento) {
        case CON_EV_WIFI_UP:   return (con_transicion_t){"T05", CON_ARRANQUE, CON_ACC_PERSISTIR};
        case CON_EV_WIFI_DOWN: return (con_transicion_t){"T06", CON_PORTAL, CON_ACC_RESPONDER_NO_CONECTA};
        case CON_EV_ENVIO:     return (con_transicion_t){"T07", CON_VALIDANDO, CON_ACC_RESPONDER_OCUPADO};
        default: break;
        }
    }
    if (origen == CON_CONECTANDO_WIFI && evento == CON_EV_WIFI_UP)
        return (con_transicion_t){"T08", CON_CONECTANDO_BROKER, CON_ACC_RED_LISTA};
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
