/* L2 conectividad — tabla de transiciones (FSD §6.3). Núcleo puro.
 * Solo contiene las filas ya implementadas; para el resto devuelve fila NULL
 * («la tabla aún no lo trata»), que no es ni «ign» ni «imp» de §6.4. */
#include "conectividad.h"
#include <stddef.h>

static const char *const NOMBRE_ESTADO[CON_N_ESTADOS] = {
    "ARRANQUE", "PORTAL", "VALIDANDO", "CONECTANDO_WIFI",
    "CONECTANDO_BROKER", "OPERATIVO", "OTA_DESCARGA", "ESPERA",
};
static const char *const NOMBRE_EVENTO[CON_N_EVENTOS] = {
    "fin_arranque", "envío", "wifi_up", "wifi_down", "backoff", "mqtt_up", "mqtt_down",
    "portal_vence", "cmd_ota", "ota_ok", "ota_err", "validacion_vence",
};

con_transicion_t con_transicion(con_estado_t origen, con_evento_t evento, con_guardas_t g)
{
    if (origen == CON_ARRANQUE && evento == CON_EV_FIN_ARRANQUE) {
        return g.config_valida
            ? (con_transicion_t){"T01", CON_CONECTANDO_WIFI, CON_ACC_ARRANCAR_STA}
            : (con_transicion_t){"T02", CON_PORTAL, CON_ACC_ARRANCAR_PORTAL};
    }
    /* T23 (región de validación, ortogonal a la principal): desde cualquier estado */
    if (evento == CON_EV_VALIDACION_VENCE)
        return g.imagen_pendiente ? (con_transicion_t){"T23", CON_ARRANQUE, CON_ACC_ROLLBACK}
                                  : (con_transicion_t){NULL, origen, CON_ACC_NINGUNA};
    if (origen == CON_OPERATIVO && evento == CON_EV_CMD_OTA)
        return g.ota_admitido ? (con_transicion_t){"T17", CON_OTA_DESCARGA, CON_ACC_INICIAR_DESCARGA}
                              : (con_transicion_t){"T18", CON_OPERATIVO, CON_ACC_RECHAZAR_OTA};
    if (origen == CON_OTA_DESCARGA) {
        switch (evento) {
        case CON_EV_OTA_OK:    return (con_transicion_t){"T19", CON_ARRANQUE, CON_ACC_REINICIAR_NUEVA};
        case CON_EV_OTA_ERR:   return (con_transicion_t){"T20", CON_OPERATIVO, CON_ACC_OTA_FALLIDA};
        case CON_EV_CMD_OTA:   return (con_transicion_t){"T21", CON_OTA_DESCARGA, CON_ACC_RECHAZAR_OCUPADO};
        case CON_EV_WIFI_DOWN: return (con_transicion_t){"T22", CON_CONECTANDO_WIFI, CON_ACC_ABORTAR_WIFI};
        case CON_EV_MQTT_DOWN: return (con_transicion_t){"T22", CON_CONECTANDO_BROKER, CON_ACC_ABORTAR_MQTT};
        default: break;                  /* wifi_up, backoff, mqtt_up: ign (§6.4) */
        }
    }
    if (origen == CON_PORTAL && evento == CON_EV_PORTAL_VENCE)
        return (con_transicion_t){"T24", CON_ESPERA, CON_ACC_CERRAR_PORTAL};
    if (origen == CON_VALIDANDO && evento == CON_EV_PORTAL_VENCE)
        return (con_transicion_t){"T25", CON_VALIDANDO, CON_ACC_APLAZAR_CIERRE};
    if (origen == CON_PORTAL && evento == CON_EV_ENVIO) {
        if (g.cierre_pendiente)          /* T26 (FSD 0.9.9): nadie alarga la ventana de 10 min */
            return (con_transicion_t){"T26", CON_PORTAL, CON_ACC_RESPONDER_OCUPADO};
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
    if (origen == CON_CONECTANDO_WIFI) {
        switch (evento) {
        case CON_EV_WIFI_UP:   return (con_transicion_t){"T08", CON_CONECTANDO_BROKER, CON_ACC_RED_LISTA};
        case CON_EV_WIFI_DOWN: return (con_transicion_t){"T09", CON_CONECTANDO_WIFI, CON_ACC_PROGRAMAR_REINTENTO};
        case CON_EV_BACKOFF:   return (con_transicion_t){"T10", CON_CONECTANDO_WIFI, CON_ACC_INTENTAR_UNION};
        default: break;
        }
    }
    if (origen == CON_CONECTANDO_BROKER) {
        switch (evento) {
        case CON_EV_MQTT_UP:   return (con_transicion_t){"T11", CON_OPERATIVO, CON_ACC_MQTT_LISTO};
        case CON_EV_MQTT_DOWN: return (con_transicion_t){"T12", CON_CONECTANDO_BROKER, CON_ACC_PROGRAMAR_REINTENTO_MQTT};
        case CON_EV_BACKOFF:   return (con_transicion_t){"T13", CON_CONECTANDO_BROKER, CON_ACC_INTENTAR_MQTT};
        case CON_EV_WIFI_DOWN: return (con_transicion_t){"T14", CON_CONECTANDO_WIFI, CON_ACC_RED_CAIDA};
        default: break;                  /* wifi_up: ign (§6.4) */
        }
    }
    if (origen == CON_OPERATIVO) {
        switch (evento) {
        case CON_EV_MQTT_DOWN: return (con_transicion_t){"T15", CON_CONECTANDO_BROKER, CON_ACC_PROGRAMAR_REINTENTO_MQTT};
        case CON_EV_WIFI_DOWN: return (con_transicion_t){"T16", CON_CONECTANDO_WIFI, CON_ACC_RED_CAIDA};
        default: break;                  /* wifi_up, backoff, mqtt_up: ign (§6.4) */
        }
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
