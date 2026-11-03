/* TC-CON-01 · T01–T23 (host, lógica de la tabla), filas implementadas: T01, T02.
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

    /* Nombres de la línea E0 (§18) */
    ESPERA(strcmp(con_nombre_estado(CON_ARRANQUE), "ARRANQUE") == 0, "nombre ARRANQUE");
    ESPERA(strcmp(con_nombre_estado(CON_PORTAL), "PORTAL") == 0, "nombre PORTAL");
    ESPERA(strcmp(con_nombre_estado(CON_CONECTANDO_WIFI), "CONECTANDO_WIFI") == 0, "nombre CONECTANDO_WIFI");
    ESPERA(strcmp(con_nombre_evento(CON_EV_FIN_ARRANQUE), "fin_arranque") == 0, "nombre fin_arranque");

    printf("TC-CON-01 (T01, T02): %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
