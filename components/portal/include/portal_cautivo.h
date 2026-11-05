/* L1 portal — piezas puras del portal cautivo (FR-POR-02). */
#pragma once
#include <stddef.h>
#include <stdint.h>

/* IP del portal (FSD §11.1). */
#define PORTAL_IP_TXT "192.168.4.1"
#define PORTAL_URL    "http://" PORTAL_IP_TXT "/"

/* 1 si un GET a uri debe responderse con 302 a PORTAL_URL: toda ruta salvo
 * «/» (incluidas /generate_204 y /hotspot-detect.html); 0 para «/». */
int portal_redirige(const char *uri);

/* Respuesta DNS a la consulta q (n bytes): toda consulta A (o ANY) de clase
 * IN se contesta con ip; otro tipo, NOERROR sin respuestas. Devuelve la
 * longitud escrita en out, o 0 si la consulta no es válida o no cabe (se
 * descarta sin responder). */
size_t portal_dns_respuesta(const uint8_t *q, size_t n, uint8_t *out, size_t cap, const uint8_t ip[4]);
