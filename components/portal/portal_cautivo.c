/* L1 portal — piezas puras del portal cautivo (FR-POR-02). */
#include "portal_cautivo.h"
#include <string.h>

int portal_redirige(const char *uri)
{
    return !(uri && strcmp(uri, "/") == 0);
}

#define DNS_CAB 12

size_t portal_dns_respuesta(const uint8_t *q, size_t n, uint8_t *out, size_t cap, const uint8_t ip[4])
{
    if (!q || n < DNS_CAB || n > 512) return 0;
    if (q[2] & 0x80) return 0;                      /* es una respuesta */
    if (((q[2] >> 3) & 0x0F) != 0) return 0;        /* solo consultas estándar */
    if (q[4] != 0 || q[5] != 1) return 0;           /* exactamente una pregunta */

    size_t i = DNS_CAB;                             /* recorrer QNAME sin punteros */
    while (i < n && q[i] != 0) {
        if (q[i] & 0xC0) return 0;
        if (i + 1 + q[i] >= n) return 0;
        i += 1 + q[i];
    }
    if (i >= n) return 0;
    i++;                                            /* el 0 final */
    if (i + 4 > n) return 0;
    uint16_t tipo = (uint16_t)(q[i] << 8 | q[i + 1]);
    uint16_t clase = (uint16_t)(q[i + 2] << 8 | q[i + 3]);
    size_t fin_pregunta = i + 4;

    int responde_a = (tipo == 1 || tipo == 255) && clase == 1;
    size_t largo = fin_pregunta + (responde_a ? 16 : 0);
    if (largo > cap) return 0;

    memcpy(out, q, fin_pregunta);                   /* id + pregunta; se descarta EDNS */
    out[2] = (uint8_t)(0x80 | 0x04 | (q[2] & 0x01)); /* QR, AA, RD copiado */
    out[3] = 0x80;                                  /* RA, NOERROR */
    out[6] = 0; out[7] = (uint8_t)(responde_a ? 1 : 0);
    out[8] = out[9] = out[10] = out[11] = 0;
    if (responde_a) {
        uint8_t *p = out + fin_pregunta;
        const uint8_t r[12] = {0xC0, 0x0C, 0, 1, 0, 1, 0, 0, 0, 60, 0, 4};   /* puntero, A, IN, TTL 60, 4 bytes */
        memcpy(p, r, sizeof r);
        memcpy(p + 12, ip, 4);
    }
    return largo;
}

void portal_ruta_log(const char *uri, char *out, size_t cap)
{
    if (!out || cap == 0) return;
    size_t n = 0;
    for (const char *p = uri; p && *p && *p != '?' && *p != '#' && n + 1 < cap; p++)
        out[n++] = (*p > 0x20 && *p < 0x7f) ? *p : '_';
    out[n] = '\0';
}
