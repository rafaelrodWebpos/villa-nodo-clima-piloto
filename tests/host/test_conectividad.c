/* TC-CON-01 · T01–T25 (host, lógica de la tabla), filas implementadas: T01–T26 (T17–T23 en el núcleo; sus acciones, en el adaptador OTA).
 * Por fila: forzar el estado de origen, inyectar el evento, comprobar la guarda,
 * el estado siguiente, la acción y el «No debe ocurrir» (FSD §6.3, §6.6). */
#include <stdio.h>
#include <string.h>
#include "conectividad.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    con_transicion_t t;

    /* T01: ARRANQUE + fin_arranque, configuración válida -> CONECTANDO_WIFI, arrancar STA. No debe: abrir el AP */
    t = con_transicion(CON_ARRANQUE, CON_EV_FIN_ARRANQUE, (con_guardas_t){.config_valida = true});
    ESPERA(t.fila && strcmp(t.fila, "T01") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_CONECTANDO_WIFI, "siguiente %d", t.siguiente);
    ESPERA(t.accion == CON_ACC_ARRANCAR_STA, "acción %d", t.accion);
    ESPERA(t.accion != CON_ACC_ARRANCAR_PORTAL, "T01 abre el AP");

    /* T02: ARRANQUE + fin_arranque, sin configuración válida -> PORTAL, arrancar portal. No debe: intentar el STA */
    t = con_transicion(CON_ARRANQUE, CON_EV_FIN_ARRANQUE, (con_guardas_t){.config_valida = false});
    ESPERA(t.fila && strcmp(t.fila, "T02") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_PORTAL, "siguiente %d", t.siguiente);
    ESPERA(t.accion == CON_ACC_ARRANCAR_PORTAL, "acción %d", t.accion);
    ESPERA(t.accion != CON_ACC_ARRANCAR_STA, "T02 intenta el STA");

    /* T03: PORTAL + envío, algún campo inválido -> PORTAL, responder con errores. No debe: escribir en la NVS */
    t = con_transicion(CON_PORTAL, CON_EV_ENVIO, (con_guardas_t){.envio_valido = false});
    ESPERA(t.fila && strcmp(t.fila, "T03") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_PORTAL, "siguiente %d", t.siguiente);
    ESPERA(t.accion == CON_ACC_RESPONDER_ERRORES, "acción %d", t.accion);
    ESPERA(t.accion != CON_ACC_PERSISTIR, "T03 escribe en la NVS");

    /* T04: PORTAL + envío, todos válidos -> VALIDANDO, probar la unión. No debe: escribir en la NVS */
    t = con_transicion(CON_PORTAL, CON_EV_ENVIO, (con_guardas_t){.envio_valido = true});
    ESPERA(t.fila && strcmp(t.fila, "T04") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_VALIDANDO && t.accion == CON_ACC_PROBAR_UNION, "T04: %d/%d", t.siguiente, t.accion);
    ESPERA(t.accion != CON_ACC_PERSISTIR, "T04 escribe en la NVS");

    /* T05: VALIDANDO + wifi_up -> ARRANQUE (reinicio), persistir */
    t = con_transicion(CON_VALIDANDO, CON_EV_WIFI_UP, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T05") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_ARRANQUE && t.accion == CON_ACC_PERSISTIR, "T05: %d/%d", t.siguiente, t.accion);

    /* T06: VALIDANDO + wifi_down (o 20 s sin IP) -> PORTAL, «no se pudo conectar». No debe: persistir */
    t = con_transicion(CON_VALIDANDO, CON_EV_WIFI_DOWN, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T06") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_PORTAL && t.accion == CON_ACC_RESPONDER_NO_CONECTA, "T06: %d/%d", t.siguiente, t.accion);
    ESPERA(t.accion != CON_ACC_PERSISTIR, "T06 persiste");

    /* T07: VALIDANDO + envío -> VALIDANDO, «ocupado». No debe: iniciar una segunda prueba */
    for (int v = 0; v < 2; v++) {
        t = con_transicion(CON_VALIDANDO, CON_EV_ENVIO, (con_guardas_t){.envio_valido = v});
        ESPERA(t.fila && strcmp(t.fila, "T07") == 0, "fila %s", t.fila ? t.fila : "NULL");
        ESPERA(t.siguiente == CON_VALIDANDO && t.accion == CON_ACC_RESPONDER_OCUPADO, "T07: %d/%d", t.siguiente, t.accion);
        ESPERA(t.accion != CON_ACC_PROBAR_UNION, "T07 inicia una segunda prueba");
    }

    /* T08: CONECTANDO_WIFI + wifi_up -> CONECTANDO_BROKER; reiniciar el backoff de Wi-Fi
     * (y, en la Fase 2, arrancar SNTP y MQTT). No debe: abrir el AP; publicar antes de T11 */
    t = con_transicion(CON_CONECTANDO_WIFI, CON_EV_WIFI_UP, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T08") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_CONECTANDO_BROKER, "siguiente %d", t.siguiente);
    ESPERA(t.accion == CON_ACC_RED_LISTA, "acción %d", t.accion);
    ESPERA(t.accion != CON_ACC_ARRANCAR_PORTAL, "T08 abre el AP");
    ESPERA(t.siguiente != CON_OPERATIVO, "T08 pasa a OPERATIVO sin T11");
    ESPERA(strcmp(con_nombre_estado(CON_CONECTANDO_BROKER), "CONECTANDO_BROKER") == 0, "nombre CONECTANDO_BROKER");

    /* T09: CONECTANDO_WIFI + wifi_down (intento fallido) -> CONECTANDO_WIFI, programar el
     * reintento con el backoff. No debe: reiniciar el nodo; abrir el AP */
    t = con_transicion(CON_CONECTANDO_WIFI, CON_EV_WIFI_DOWN, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T09") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_CONECTANDO_WIFI && t.accion == CON_ACC_PROGRAMAR_REINTENTO, "T09: %d/%d", t.siguiente, t.accion);
    ESPERA(t.accion != CON_ACC_ARRANCAR_PORTAL && t.accion != CON_ACC_PERSISTIR, "T09 abre el AP o reinicia");

    /* T10: CONECTANDO_WIFI + backoff -> CONECTANDO_WIFI, lanzar un intento de unión. No debe: abrir el AP */
    t = con_transicion(CON_CONECTANDO_WIFI, CON_EV_BACKOFF, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T10") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_CONECTANDO_WIFI && t.accion == CON_ACC_INTENTAR_UNION, "T10: %d/%d", t.siguiente, t.accion);
    ESPERA(strcmp(con_nombre_evento(CON_EV_BACKOFF), "backoff") == 0, "nombre backoff");

    /* T11: CONECTANDO_BROKER + mqtt_up -> OPERATIVO; publicar status online, luego Discovery,
     * luego las medidas; reiniciar el backoff MQTT. No debe: publicar medidas antes que status */
    t = con_transicion(CON_CONECTANDO_BROKER, CON_EV_MQTT_UP, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T11") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_OPERATIVO && t.accion == CON_ACC_MQTT_LISTO, "T11: %d/%d", t.siguiente, t.accion);

    /* T12: CONECTANDO_BROKER + mqtt_down (intento fallido) -> CONECTANDO_BROKER, programar el
     * reintento MQTT con el backoff. No debe: reiniciar; desconectar el Wi-Fi */
    t = con_transicion(CON_CONECTANDO_BROKER, CON_EV_MQTT_DOWN, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T12") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_CONECTANDO_BROKER && t.accion == CON_ACC_PROGRAMAR_REINTENTO_MQTT, "T12: %d/%d", t.siguiente, t.accion);

    /* T13: CONECTANDO_BROKER + backoff -> CONECTANDO_BROKER, lanzar un intento MQTT (no de Wi-Fi) */
    t = con_transicion(CON_CONECTANDO_BROKER, CON_EV_BACKOFF, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T13") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_CONECTANDO_BROKER && t.accion == CON_ACC_INTENTAR_MQTT, "T13: %d/%d", t.siguiente, t.accion);

    /* T14: CONECTANDO_BROKER + wifi_down -> CONECTANDO_WIFI; detener MQTT y programar el reintento Wi-Fi. No debe: reiniciar */
    t = con_transicion(CON_CONECTANDO_BROKER, CON_EV_WIFI_DOWN, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T14") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_CONECTANDO_WIFI && t.accion == CON_ACC_RED_CAIDA, "T14: %d/%d", t.siguiente, t.accion);

    /* T15: OPERATIVO + mqtt_down -> CONECTANDO_BROKER, programar el reintento MQTT. No debe: reiniciar; desconectar el Wi-Fi */
    t = con_transicion(CON_OPERATIVO, CON_EV_MQTT_DOWN, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T15") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_CONECTANDO_BROKER && t.accion == CON_ACC_PROGRAMAR_REINTENTO_MQTT, "T15: %d/%d", t.siguiente, t.accion);

    /* T16: OPERATIVO + wifi_down -> CONECTANDO_WIFI, programar el reintento Wi-Fi. No debe: reiniciar */
    t = con_transicion(CON_OPERATIVO, CON_EV_WIFI_DOWN, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T16") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_CONECTANDO_WIFI && t.accion == CON_ACC_RED_CAIDA, "T16: %d/%d", t.siguiente, t.accion);

    /* «ign» de §6.4: sin transición ni acción (CONECTANDO_BROKER + wifi_up; OPERATIVO + wifi_up, backoff, mqtt_up) */
    const struct { con_estado_t e; con_evento_t ev; } ign[] = {
        {CON_CONECTANDO_BROKER, CON_EV_WIFI_UP}, {CON_OPERATIVO, CON_EV_WIFI_UP},
        {CON_OPERATIVO, CON_EV_BACKOFF}, {CON_OPERATIVO, CON_EV_MQTT_UP}};
    for (unsigned i = 0; i < sizeof ign / sizeof ign[0]; i++) {
        t = con_transicion(ign[i].e, ign[i].ev, (con_guardas_t){0});
        ESPERA(t.fila == NULL && t.accion == CON_ACC_NINGUNA && t.siguiente == ign[i].e, "ign %u con fila %s", i, t.fila ? t.fila : "NULL");
    }
    ESPERA(strcmp(con_nombre_evento(CON_EV_MQTT_UP), "mqtt_up") == 0, "nombre mqtt_up");
    ESPERA(strcmp(con_nombre_evento(CON_EV_MQTT_DOWN), "mqtt_down") == 0, "nombre mqtt_down");
    ESPERA(strcmp(con_nombre_estado(CON_OPERATIVO), "OPERATIVO") == 0, "nombre OPERATIVO");

    /* Fuera de VALIDANDO, wifi_up/wifi_down no tienen fila todavía (no se inventa) */
    t = con_transicion(CON_PORTAL, CON_EV_WIFI_DOWN, (con_guardas_t){0});
    ESPERA(t.fila == NULL && t.accion == CON_ACC_NINGUNA, "PORTAL + wifi_down tiene fila %s", t.fila ? t.fila : "NULL");

    /* Nombres de la línea E0 (§18) */
    ESPERA(strcmp(con_nombre_evento(CON_EV_WIFI_UP), "wifi_up") == 0, "nombre wifi_up");
    ESPERA(strcmp(con_nombre_evento(CON_EV_WIFI_DOWN), "wifi_down") == 0, "nombre wifi_down");
    ESPERA(strcmp(con_nombre_estado(CON_VALIDANDO), "VALIDANDO") == 0, "nombre VALIDANDO");
    ESPERA(strcmp(con_nombre_evento(CON_EV_ENVIO), "envío") == 0, "nombre envío");
    ESPERA(strcmp(con_nombre_estado(CON_ARRANQUE), "ARRANQUE") == 0, "nombre ARRANQUE");
    ESPERA(strcmp(con_nombre_estado(CON_PORTAL), "PORTAL") == 0, "nombre PORTAL");
    ESPERA(strcmp(con_nombre_estado(CON_CONECTANDO_WIFI), "CONECTANDO_WIFI") == 0, "nombre CONECTANDO_WIFI");
    ESPERA(strcmp(con_nombre_evento(CON_EV_FIN_ARRANQUE), "fin_arranque") == 0, "nombre fin_arranque");

    /* T24: PORTAL + portal_vence -> ESPERA, cerrar el portal. No debe: mantener el AP, escribir en la NVS, reiniciar */
    t = con_transicion(CON_PORTAL, CON_EV_PORTAL_VENCE, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T24") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_ESPERA && t.accion == CON_ACC_CERRAR_PORTAL, "T24: %d/%d", t.siguiente, t.accion);
    ESPERA(t.accion != CON_ACC_PERSISTIR, "T24 escribe en la NVS");

    /* T25: VALIDANDO + portal_vence -> VALIDANDO, aplazar el cierre. No debe: interrumpir la prueba */
    t = con_transicion(CON_VALIDANDO, CON_EV_PORTAL_VENCE, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T25") == 0, "fila %s", t.fila ? t.fila : "NULL");
    ESPERA(t.siguiente == CON_VALIDANDO && t.accion == CON_ACC_APLAZAR_CIERRE, "T25: %d/%d", t.siguiente, t.accion);
    ESPERA(t.accion != CON_ACC_RESPONDER_NO_CONECTA && t.accion != CON_ACC_CERRAR_PORTAL, "T25 interrumpe la prueba");
    /* ...y la prueba termina por T06 (vuelve a PORTAL, donde el evento repetido da T24) o por T05 */
    t = con_transicion(CON_VALIDANDO, CON_EV_WIFI_DOWN, (con_guardas_t){0});
    ESPERA(t.siguiente == CON_PORTAL, "T06 tras T25: %d", t.siguiente);
    t = con_transicion(t.siguiente, CON_EV_PORTAL_VENCE, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T24") == 0 && t.siguiente == CON_ESPERA, "T24 tras T06: %s", t.fila ? t.fila : "NULL");
    t = con_transicion(CON_VALIDANDO, CON_EV_WIFI_UP, (con_guardas_t){0});
    ESPERA(t.siguiente == CON_ARRANQUE && t.accion == CON_ACC_PERSISTIR, "T05 tras T25: %d/%d", t.siguiente, t.accion);

    /* T26: PORTAL + envío con el cierre pendiente -> PORTAL, «ocupado». No debe: probar la unión (alargaría la ventana) */
    for (int valido = 0; valido <= 1; valido++) {
        t = con_transicion(CON_PORTAL, CON_EV_ENVIO, (con_guardas_t){.envio_valido = valido, .cierre_pendiente = true});
        ESPERA(t.fila && strcmp(t.fila, "T26") == 0, "fila %s (válido=%d)", t.fila ? t.fila : "NULL", valido);
        ESPERA(t.siguiente == CON_PORTAL && t.accion == CON_ACC_RESPONDER_OCUPADO, "T26: %d/%d", t.siguiente, t.accion);
        ESPERA(t.accion != CON_ACC_PROBAR_UNION && t.accion != CON_ACC_PERSISTIR, "T26 prueba la unión o escribe");
    }
    /* sin cierre pendiente, T03/T04 como siempre */
    t = con_transicion(CON_PORTAL, CON_EV_ENVIO, (con_guardas_t){.envio_valido = true});
    ESPERA(t.fila && strcmp(t.fila, "T04") == 0, "sin cierre pendiente: %s", t.fila ? t.fila : "NULL");

    /* ESPERA: ningún evento tiene fila (§6.4: todos imp); portal_vence fuera de PORTAL/VALIDANDO tampoco */
    for (int ev = 0; ev < CON_N_EVENTOS; ev++) {
        t = con_transicion(CON_ESPERA, (con_evento_t)ev, (con_guardas_t){0});
        ESPERA(t.fila == NULL && t.siguiente == CON_ESPERA, "ESPERA + %s: fila %s", con_nombre_evento(ev), t.fila ? t.fila : "NULL");
    }
    const con_estado_t otros[] = {CON_ARRANQUE, CON_CONECTANDO_WIFI, CON_CONECTANDO_BROKER, CON_OPERATIVO};
    for (unsigned i = 0; i < sizeof otros / sizeof otros[0]; i++) {
        t = con_transicion(otros[i], CON_EV_PORTAL_VENCE, (con_guardas_t){0});
        ESPERA(t.fila == NULL, "%s + portal_vence: fila %s", con_nombre_estado(otros[i]), t.fila);
    }
    ESPERA(strcmp(con_nombre_estado(CON_ESPERA), "ESPERA") == 0, "nombre ESPERA");
    ESPERA(strcmp(con_nombre_evento(CON_EV_PORTAL_VENCE), "portal_vence") == 0, "nombre portal_vence");

    /* T17: OPERATIVO + cmd_ota admitido -> OTA_DESCARGA, iniciar la descarga */
    t = con_transicion(CON_OPERATIVO, CON_EV_CMD_OTA, (con_guardas_t){.ota_admitido = true});
    ESPERA(t.fila && strcmp(t.fila, "T17") == 0 && t.siguiente == CON_OTA_DESCARGA && t.accion == CON_ACC_INICIAR_DESCARGA,
           "T17: %s %d/%d", t.fila ? t.fila : "NULL", t.siguiente, t.accion);
    /* T18: OPERATIVO + cmd_ota que incumple la guarda -> OPERATIVO, rechazar. No debe: descargar */
    t = con_transicion(CON_OPERATIVO, CON_EV_CMD_OTA, (con_guardas_t){.ota_admitido = false});
    ESPERA(t.fila && strcmp(t.fila, "T18") == 0 && t.siguiente == CON_OPERATIVO && t.accion == CON_ACC_RECHAZAR_OTA,
           "T18: %s %d/%d", t.fila ? t.fila : "NULL", t.siguiente, t.accion);
    ESPERA(t.accion != CON_ACC_INICIAR_DESCARGA, "T18 descarga");
    /* T19: OTA_DESCARGA + ota_ok -> ARRANQUE (reinicio en el slot nuevo) */
    t = con_transicion(CON_OTA_DESCARGA, CON_EV_OTA_OK, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T19") == 0 && t.siguiente == CON_ARRANQUE && t.accion == CON_ACC_REINICIAR_NUEVA, "T19");
    /* T20: OTA_DESCARGA + ota_err -> OPERATIVO, conservar la imagen. No debe: reiniciar */
    t = con_transicion(CON_OTA_DESCARGA, CON_EV_OTA_ERR, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T20") == 0 && t.siguiente == CON_OPERATIVO && t.accion == CON_ACC_OTA_FALLIDA, "T20");
    ESPERA(t.accion != CON_ACC_REINICIAR_NUEVA && t.accion != CON_ACC_ROLLBACK, "T20 reinicia");
    /* T21: OTA_DESCARGA + cmd_ota -> OTA_DESCARGA, «ocupado». No debe: abortar la descarga en curso */
    for (int adm = 0; adm <= 1; adm++) {
        t = con_transicion(CON_OTA_DESCARGA, CON_EV_CMD_OTA, (con_guardas_t){.ota_admitido = adm});
        ESPERA(t.fila && strcmp(t.fila, "T21") == 0 && t.siguiente == CON_OTA_DESCARGA && t.accion == CON_ACC_RECHAZAR_OCUPADO,
               "T21 (admitido=%d)", adm);
    }
    /* T22: OTA_DESCARGA + wifi_down / mqtt_down -> CONECTANDO_WIFI / CONECTANDO_BROKER, abortar. No debe: reiniciar */
    t = con_transicion(CON_OTA_DESCARGA, CON_EV_WIFI_DOWN, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T22") == 0 && t.siguiente == CON_CONECTANDO_WIFI && t.accion == CON_ACC_ABORTAR_WIFI, "T22 wifi");
    t = con_transicion(CON_OTA_DESCARGA, CON_EV_MQTT_DOWN, (con_guardas_t){0});
    ESPERA(t.fila && strcmp(t.fila, "T22") == 0 && t.siguiente == CON_CONECTANDO_BROKER && t.accion == CON_ACC_ABORTAR_MQTT, "T22 mqtt");
    /* T23: imagen PENDIENTE + 300 s sin T11 -> reinicio con rollback, desde cualquier estado; sin PENDIENTE, nada */
    for (int e = 0; e < CON_N_ESTADOS; e++) {
        t = con_transicion((con_estado_t)e, CON_EV_VALIDACION_VENCE, (con_guardas_t){.imagen_pendiente = true});
        ESPERA(t.fila && strcmp(t.fila, "T23") == 0 && t.accion == CON_ACC_ROLLBACK, "T23 desde %s", con_nombre_estado(e));
        t = con_transicion((con_estado_t)e, CON_EV_VALIDACION_VENCE, (con_guardas_t){0});
        ESPERA(t.fila == NULL && t.siguiente == (con_estado_t)e, "T23 sin PENDIENTE desde %s", con_nombre_estado(e));
    }
    /* §6.4: OTA_DESCARGA ignora wifi_up, backoff y mqtt_up; cmd_ota es imp fuera de OPERATIVO/OTA_DESCARGA;
     * ota_ok/ota_err son imp fuera de OTA_DESCARGA */
    const con_evento_t ign_ota[] = {CON_EV_WIFI_UP, CON_EV_BACKOFF, CON_EV_MQTT_UP};
    for (unsigned i = 0; i < sizeof ign_ota / sizeof ign_ota[0]; i++) {
        t = con_transicion(CON_OTA_DESCARGA, ign_ota[i], (con_guardas_t){0});
        ESPERA(t.fila == NULL && t.siguiente == CON_OTA_DESCARGA, "OTA_DESCARGA + %s", con_nombre_evento(ign_ota[i]));
    }
    for (int e = 0; e < CON_N_ESTADOS; e++) {
        if (e != CON_OPERATIVO && e != CON_OTA_DESCARGA) {
            t = con_transicion((con_estado_t)e, CON_EV_CMD_OTA, (con_guardas_t){.ota_admitido = true});
            ESPERA(t.fila == NULL, "%s + cmd_ota: %s", con_nombre_estado(e), t.fila);
        }
        if (e != CON_OTA_DESCARGA) {
            t = con_transicion((con_estado_t)e, CON_EV_OTA_OK, (con_guardas_t){0});
            ESPERA(t.fila == NULL, "%s + ota_ok: %s", con_nombre_estado(e), t.fila);
            t = con_transicion((con_estado_t)e, CON_EV_OTA_ERR, (con_guardas_t){0});
            ESPERA(t.fila == NULL, "%s + ota_err: %s", con_nombre_estado(e), t.fila);
        }
    }
    ESPERA(strcmp(con_nombre_estado(CON_OTA_DESCARGA), "OTA_DESCARGA") == 0, "nombre OTA_DESCARGA");
    ESPERA(strcmp(con_nombre_evento(CON_EV_CMD_OTA), "cmd_ota") == 0 && strcmp(con_nombre_evento(CON_EV_OTA_OK), "ota_ok") == 0
           && strcmp(con_nombre_evento(CON_EV_OTA_ERR), "ota_err") == 0, "nombres de evento de §18 (E0)");

    printf("TC-CON-01 (T01–T26): %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
