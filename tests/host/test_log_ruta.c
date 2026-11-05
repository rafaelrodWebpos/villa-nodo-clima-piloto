/* TC-SEC-02 · FR-SEC-03 (host): el log de páginas del portal nunca escribe la
 * consulta de una URL (ahí podría ir un dato del formulario), ni caracteres no
 * imprimibles, ni más de lo que cabe. */
#include <stdio.h>
#include <string.h>
#include "portal_cautivo.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

int main(void)
{
    char r[41];
    portal_ruta_log("/", r, sizeof r);                       ESPERA(strcmp(r, "/") == 0, "'%s'", r);
    portal_ruta_log("/generate_204", r, sizeof r);           ESPERA(strcmp(r, "/generate_204") == 0, "'%s'", r);
    portal_ruta_log("/?wifi_pass=SECRETO1", r, sizeof r);    ESPERA(strcmp(r, "/") == 0 && !strstr(r, "SECRETO"), "consulta en el log: '%s'", r);
    portal_ruta_log("/x#wifi_pass=SECRETO2", r, sizeof r);   ESPERA(strcmp(r, "/x") == 0, "fragmento en el log: '%s'", r);
    portal_ruta_log("/a b\n\x01" "c", r, sizeof r);          ESPERA(strcmp(r, "/a_b__c") == 0, "no imprimibles: '%s'", r);
    char largo[100]; memset(largo, 'z', sizeof largo - 1); largo[0] = '/'; largo[99] = 0;
    portal_ruta_log(largo, r, sizeof r);                     ESPERA(strlen(r) == sizeof r - 1, "longitud %zu", strlen(r));
    portal_ruta_log(NULL, r, sizeof r);                      ESPERA(strcmp(r, "") == 0, "NULL: '%s'", r);
    printf("TC-SEC-02 (FR-SEC-03): %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
