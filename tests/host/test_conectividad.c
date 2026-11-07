/* TC-CON-01 · T01–T23 (host, lógica de la tabla), filas implementadas: T01–T16.
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

    printf("TC-CON-01 (T01–T16): %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
