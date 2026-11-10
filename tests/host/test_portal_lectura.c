/* TC-POR-13 · FR-POR-09 (host): un POST cuyo cuerpo no llega tras 3 esperas seguidas sin
 * datos se corta con 408; con datos entre medias no se corta; un error de socket corta sin
 * respuesta; nunca se espera sin límite (FSD §11.2, D25, SEC-05). */
#include <stdio.h>
#include "portal_lectura.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    int e = 0;
    /* 2 esperas y luego datos: seguir */
    ESPERA(portal_lectura_paso(0, 1, &e) == PORTAL_LECTURA_ESPERAR, "1.ª espera");
    ESPERA(portal_lectura_paso(0, 1, &e) == PORTAL_LECTURA_ESPERAR, "2.ª espera");
    ESPERA(portal_lectura_paso(100, 0, &e) == PORTAL_LECTURA_DATOS && e == 0, "datos tras 2 esperas: %d", e);
    /* el contador es de esperas SEGUIDAS: tras datos vuelven a hacer falta 3 */
    ESPERA(portal_lectura_paso(0, 1, &e) == PORTAL_LECTURA_ESPERAR, "espera tras datos");
    ESPERA(portal_lectura_paso(0, 1, &e) == PORTAL_LECTURA_ESPERAR, "2.ª espera tras datos");
    ESPERA(portal_lectura_paso(0, 1, &e) == PORTAL_LECTURA_408, "3.ª espera seguida: 408");
    /* 3 esperas seguidas desde el principio: 408 a la tercera, no antes */
    e = 0;
    portal_lectura_t r1 = portal_lectura_paso(0, 1, &e), r2 = portal_lectura_paso(0, 1, &e), r3 = portal_lectura_paso(0, 1, &e);
    ESPERA(r1 == PORTAL_LECTURA_ESPERAR && r2 == PORTAL_LECTURA_ESPERAR && r3 == PORTAL_LECTURA_408, "%d %d %d", r1, r2, r3);
    /* sin límite nunca: mil esperas seguidas dan 408 en cuanto se llega a 3 */
    e = 0;
    int n408 = 0;
    for (int i = 0; i < 1000; i++) if (portal_lectura_paso(0, 1, &e) == PORTAL_LECTURA_408) { n408 = i + 1; break; }
    ESPERA(n408 == PORTAL_ESPERAS_MAX, "408 a la espera %d", n408);
    /* datos llegando nunca dan 408 */
    e = 0;
    for (int i = 0; i < 100; i++) ESPERA(portal_lectura_paso(10, 0, &e) == PORTAL_LECTURA_DATOS, "datos %d", i);
    /* error de socket o cierre del cliente: cortar */
    e = 0;
    ESPERA(portal_lectura_paso(0, 0, &e) == PORTAL_LECTURA_CORTAR, "cierre del cliente");
    ESPERA(portal_lectura_paso(-1, 0, &e) == PORTAL_LECTURA_CORTAR, "error de socket");
    printf("TC-POR-13: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
