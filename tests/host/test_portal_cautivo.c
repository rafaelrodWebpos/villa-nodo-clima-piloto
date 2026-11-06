/* TC-POR-06 · FR-POR-02 (host): redirección de toda ruta salvo «/» y
 * respuesta DNS que resuelve cualquier nombre a 192.168.4.1. */
#include <stdio.h>
#include <string.h>
#include "portal_cautivo.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

/* Consulta DNS de un nombre (labels separados por puntos), tipo y clase dados */
static size_t consulta(uint8_t *q, const char *nombre, uint16_t tipo, uint16_t clase, int con_edns)
{
    uint8_t h[12] = {0xAB, 0xCD, 0x01, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, (uint8_t)(con_edns ? 1 : 0)};
    memcpy(q, h, 12);
    size_t i = 12;
    const char *p = nombre;
    while (*p) {
        const char *punto = strchr(p, '.');
        size_t l = punto ? (size_t)(punto - p) : strlen(p);
        q[i++] = (uint8_t)l; memcpy(q + i, p, l); i += l;
        p += l; if (*p == '.') p++;
    }
    q[i++] = 0;
    q[i++] = (uint8_t)(tipo >> 8); q[i++] = (uint8_t)tipo; q[i++] = (uint8_t)(clase >> 8); q[i++] = (uint8_t)clase;
    if (con_edns) { const uint8_t opt[] = {0, 0, 41, 0x10, 0, 0, 0, 0, 0, 0, 0}; memcpy(q + i, opt, sizeof opt); i += sizeof opt; }
    return i;
}

int main(void)
{
    /* Redirección (FR-POR-02): las dos rutas del contrato, otras, y «/» no */
    ESPERA(portal_redirige("/generate_204") == 1, "/generate_204 no redirige");
    ESPERA(portal_redirige("/hotspot-detect.html") == 1, "/hotspot-detect.html no redirige");
    /* FSD 0.9.5, fila host de FR-POR-02: el destino del 302 es exactamente el portal
     * (el código «302 Found» lo pone el adaptador, portal_http.c; revisión) */
    ESPERA(strcmp(PORTAL_URL, "http://192.168.4.1/") == 0, "destino del 302: '%s'", PORTAL_URL);
    ESPERA(portal_redirige("/connecttest.txt") == 1 && portal_redirige("/x/y?z=1") == 1, "otra ruta no redirige");
    ESPERA(portal_redirige("/") == 0, "«/» redirige (debe servir el formulario)");
    ESPERA(strcmp(PORTAL_URL, "http://192.168.4.1/") == 0, "PORTAL_URL = %s", PORTAL_URL);

    const uint8_t ip[4] = {192, 168, 4, 1};
    uint8_t q[512], r[512];

    /* A de clase IN, con EDNS: una respuesta A con 192.168.4.1 */
    size_t n = consulta(q, "connectivitycheck.gstatic.com", 1, 1, 1);
    size_t m = portal_dns_respuesta(q, n, r, sizeof r, ip);
    size_t qend = n - 11;                                   /* fin de la pregunta (sin el OPT) */
    ESPERA(m == qend + 16, "longitud %zu (esperada %zu)", m, qend + 16);
    ESPERA(r[0] == 0xAB && r[1] == 0xCD, "id no copiado");
    ESPERA((r[2] & 0x80) && (r[2] & 0x01), "sin QR o sin RD copiado");
    ESPERA((r[3] & 0x0F) == 0, "rcode %d", r[3] & 0x0F);
    ESPERA(r[5] == 1 && r[7] == 1 && r[9] == 0 && r[11] == 0, "qd/an/ns/ar = %d/%d/%d/%d", r[5], r[7], r[9], r[11]);
    ESPERA(memcmp(r + 12, q + 12, qend - 12) == 0, "pregunta no copiada");
    const uint8_t ans[] = {0xC0, 0x0C, 0, 1, 0, 1};
    ESPERA(memcmp(r + qend, ans, 6) == 0, "respuesta sin puntero, tipo A o clase IN");
    ESPERA(r[qend + 10] == 0 && r[qend + 11] == 4 && memcmp(r + qend + 12, ip, 4) == 0, "rdata no es 192.168.4.1");

    /* Cualquier nombre (FR-POR-02): otro nombre, misma IP */
    n = consulta(q, "example.com", 1, 1, 0);
    m = portal_dns_respuesta(q, n, r, sizeof r, ip);
    ESPERA(m == n + 16 && memcmp(r + n + 12, ip, 4) == 0, "example.com no resuelve a 192.168.4.1");

    /* AAAA: NOERROR sin respuestas (el teléfono cae a IPv4) */
    n = consulta(q, "example.com", 28, 1, 0);
    m = portal_dns_respuesta(q, n, r, sizeof r, ip);
    ESPERA(m == n && r[7] == 0 && (r[3] & 0x0F) == 0, "AAAA: m=%zu an=%d", m, r[7]);

    /* Inválidas: se descartan (0) */
    ESPERA(portal_dns_respuesta(q, 11, r, sizeof r, ip) == 0, "cabecera corta aceptada");
    n = consulta(q, "example.com", 1, 1, 0); q[2] |= 0x80;
    ESPERA(portal_dns_respuesta(q, n, r, sizeof r, ip) == 0, "una respuesta se contesta");
    n = consulta(q, "example.com", 1, 1, 0); q[5] = 2;
    ESPERA(portal_dns_respuesta(q, n, r, sizeof r, ip) == 0, "qdcount 2 aceptado");
    n = consulta(q, "example.com", 1, 1, 0);
    ESPERA(portal_dns_respuesta(q, n - 3, r, sizeof r, ip) == 0, "pregunta truncada aceptada");
    n = consulta(q, "example.com", 1, 1, 0); q[12] = 60;
    ESPERA(portal_dns_respuesta(q, n, r, sizeof r, ip) == 0, "label que se sale aceptado");
    n = consulta(q, "example.com", 1, 1, 0);
    ESPERA(portal_dns_respuesta(q, n, r, n + 15, ip) == 0, "salida que no cabe aceptada");

    printf("TC-POR-06 (FR-POR-02): %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
