/* TC-POR-13 · FR-POR-09 (host): un POST cuyo cuerpo no llega tras 3 esperas seguidas sin
 * datos, o que no está completo a los 20 s aunque lleguen datos poco a poco («1 byte por
 * espera», H-85), se corta con 408; un cuerpo completo dentro del plazo nunca; un error de
 * socket corta sin respuesta; nunca se espera sin límite (FSD §11.2, D25, SEC-05). */
#include <stdio.h>
#include "portal_lectura.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)
#define ESPERA_RECV_MS 5000           /* recv_wait_timeout de esp_http_server */

int main(void)
{
    int e = 0;
    /* 2 esperas y luego datos: seguir */
    ESPERA(portal_lectura_paso(0, 1, 5000, 0, &e) == PORTAL_LECTURA_ESPERAR, "1.ª espera");
    ESPERA(portal_lectura_paso(0, 1, 10000, 0, &e) == PORTAL_LECTURA_ESPERAR, "2.ª espera");
    ESPERA(portal_lectura_paso(100, 0, 10100, 0, &e) == PORTAL_LECTURA_DATOS && e == 0, "datos tras 2 esperas: %d", e);
    /* 3 esperas seguidas desde el principio: 408 a la tercera (15 s), no antes */
    e = 0;
    portal_lectura_t r1 = portal_lectura_paso(0, 1, 5000, 0, &e), r2 = portal_lectura_paso(0, 1, 10000, 0, &e),
                     r3 = portal_lectura_paso(0, 1, 15000, 0, &e);
    ESPERA(r1 == PORTAL_LECTURA_ESPERAR && r2 == PORTAL_LECTURA_ESPERAR && r3 == PORTAL_LECTURA_408, "%d %d %d", r1, r2, r3);

    /* «1 byte por espera»: el cliente manda 1 byte cada 4,9 s (justo antes de cada espera);
     * el contador de esperas nunca llega a 3, pero el plazo corta, y nunca después de 20 s */
    e = 0;
    int64_t t = 0, t408 = -1;
    for (int i = 0; i < 1024 && t408 < 0; i++) {
        t += 4900;
        if (portal_lectura_paso(1, 0, t, 0, &e) == PORTAL_LECTURA_408) t408 = t;
    }
    ESPERA(t408 >= 0, "1 byte por espera: nunca 408 (retiene la tarea)");
    ESPERA(t408 <= PORTAL_PLAZO_TOTAL_MS, "1 byte por espera: 408 a %lld ms > %d", (long long)t408, PORTAL_PLAZO_TOTAL_MS);
    /* el peor caso: la lectura que detecta el plazo empezó justo antes de los 15 s y esperó 5 s */
    ESPERA(PORTAL_PLAZO_CORTE_MS + ESPERA_RECV_MS <= PORTAL_PLAZO_TOTAL_MS, "el peor caso pasa de 20 s");
    /* esperas alternas con bytes sueltos: tampoco pasa de 20 s */
    e = 0; t = 0; t408 = -1;
    for (int i = 0; i < 1000 && t408 < 0; i++) {
        t += ESPERA_RECV_MS;
        if (portal_lectura_paso(i % 2 ? 1 : 0, i % 2 ? 0 : 1, t, 0, &e) == PORTAL_LECTURA_408) t408 = t;
    }
    ESPERA(t408 >= 0 && t408 <= PORTAL_PLAZO_TOTAL_MS, "esperas alternas: 408 a %lld ms", (long long)t408);

    /* cuerpo completo dentro del plazo, aunque sea al límite: nunca 408 */
    e = 0;
    ESPERA(portal_lectura_paso(300, 0, 14999, 1, &e) == PORTAL_LECTURA_DATOS, "completo a 14,999 s");
    ESPERA(portal_lectura_paso(300, 0, 19999, 1, &e) == PORTAL_LECTURA_DATOS, "completo con la última lectura a 19,999 s");
    for (int i = 0; i < 100; i++) ESPERA(portal_lectura_paso(10, 0, 100 + i, 0, &e) == PORTAL_LECTURA_DATOS, "datos %d", i);

    /* error de socket o cierre del cliente: cortar */
    e = 0;
    ESPERA(portal_lectura_paso(0, 0, 10, 0, &e) == PORTAL_LECTURA_CORTAR, "cierre del cliente");
    ESPERA(portal_lectura_paso(-1, 0, 10, 0, &e) == PORTAL_LECTURA_CORTAR, "error de socket");
    ESPERA(portal_lectura_paso(-1, 0, 30000, 0, &e) == PORTAL_LECTURA_CORTAR, "error de socket tras el plazo");
    printf("TC-POR-13: %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
