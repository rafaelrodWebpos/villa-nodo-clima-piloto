/* L2 conectividad — tabla de transiciones del gestor (FSD §6.3). Núcleo puro:
 * decide estado siguiente y acción; los adaptadores ejecutan la acción y
 * escriben la línea E0 «con: <ORIGEN> -> <DESTINO> (<evento>)» (§18). */
#pragma once
#include <stdbool.h>

typedef enum {
    CON_ARRANQUE, CON_PORTAL, CON_VALIDANDO, CON_CONECTANDO_WIFI,
    CON_CONECTANDO_BROKER, CON_OPERATIVO, CON_OTA_DESCARGA, CON_ESPERA, CON_N_ESTADOS
} con_estado_t;

typedef enum {
    CON_EV_FIN_ARRANQUE, CON_EV_ENVIO, CON_EV_WIFI_UP, CON_EV_WIFI_DOWN, CON_EV_BACKOFF,
    CON_EV_MQTT_UP, CON_EV_MQTT_DOWN,
    CON_EV_PORTAL_VENCE,                 /* FR-POR-08: 10 min desde T02 (D24) */
    CON_N_EVENTOS                        /* el resto de §6.4 llega con sus filas */
} con_evento_t;

typedef enum {
    CON_ACC_NINGUNA,
    CON_ACC_ARRANCAR_STA,      /* T01: arrancar el STA y el ciclo de medición */
    CON_ACC_ARRANCAR_PORTAL,   /* T02: arrancar el AP, el DNS, el HTTP y el ciclo de medición */
    CON_ACC_RESPONDER_ERRORES, /* T03: responder con un error por campo */
    CON_ACC_PROBAR_UNION,      /* T04: probar la unión STA (AP+STA) con los datos del formulario */
    CON_ACC_PERSISTIR,         /* T05: persistir la configuración, responder con éxito y reiniciar */
    CON_ACC_RESPONDER_NO_CONECTA, /* T06: responder «no se pudo conectar» y descartar los datos */
    CON_ACC_RESPONDER_OCUPADO, /* T07: responder «ocupado» */
    CON_ACC_RED_LISTA,         /* T08: reiniciar el backoff de Wi-Fi; arrancar SNTP y el cliente MQTT */
    CON_ACC_PROGRAMAR_REINTENTO, /* T09: programar un reintento Wi-Fi con el backoff (FR-CON-02) */
    CON_ACC_INTENTAR_UNION,    /* T10: lanzar un intento de unión */
    CON_ACC_MQTT_LISTO,        /* T11: status online, Discovery, medidas; reiniciar el backoff MQTT */
    CON_ACC_PROGRAMAR_REINTENTO_MQTT, /* T12/T15: programar un reintento MQTT con el backoff */
    CON_ACC_INTENTAR_MQTT,     /* T13: lanzar un intento de conexión MQTT */
    CON_ACC_RED_CAIDA,         /* T14/T16: detener los intentos MQTT; programar un reintento Wi-Fi */
    CON_ACC_CERRAR_PORTAL,     /* T24: detener el HTTP y el DNS del portal y apagar el AP */
    CON_ACC_APLAZAR_CIERRE,    /* T25: la prueba de unión sigue; el cierre se aplica al volver a PORTAL */
} con_accion_t;

typedef struct {
    bool config_valida;        /* guarda de T01/T02: configuración válida en NVS */
    bool envio_valido;         /* guarda de T03/T04: todos los campos válidos (§17) */
} con_guardas_t;

typedef struct {
    const char *fila;          /* «T01»…; NULL si la tabla aún no trata (estado, evento) */
    con_estado_t siguiente;
    con_accion_t accion;
} con_transicion_t;

con_transicion_t con_transicion(con_estado_t origen, con_evento_t evento, con_guardas_t g);
const char *con_nombre_estado(con_estado_t e);
const char *con_nombre_evento(con_evento_t ev);
