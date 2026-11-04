/* L1 portal — decodificación del envío urlencoded (FR-POR-04). Núcleo puro. */
#include "portal_urlenc.h"
#include <string.h>

static int hex(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

/* Decodifica s en el sitio; devuelve s. */
static char *decodificar(char *s)
{
    char *r = s, *w = s;
    while (*r) {
        if (*r == '+') { *w++ = ' '; r++; }
        else if (*r == '%' && hex(r[1]) >= 0 && hex(r[2]) >= 0) { *w++ = (char)(hex(r[1]) * 16 + hex(r[2])); r += 3; }
        else *w++ = *r++;
    }
    *w = '\0';
    return s;
}

void portal_decodificar(char *body, const char *v[PORTAL_N_CAMPOS])
{
    for (int i = 0; i < PORTAL_N_CAMPOS; i++) v[i] = NULL;
    char *p = body;
    while (p && *p) {
        char *fin = strchr(p, '&');
        if (fin) *fin = '\0';
        char *igual = strchr(p, '=');
        if (igual) {
            *igual = '\0';
            const char *clave = decodificar(p);
            for (int i = 0; i < PORTAL_N_CAMPOS; i++) {
                if (strcmp(clave, PORTAL_NAME[i]) == 0) {
                    if (!v[i]) v[i] = decodificar(igual + 1);   /* cuenta la primera */
                    break;
                }
            }
        }
        p = fin ? fin + 1 : NULL;
    }
}
