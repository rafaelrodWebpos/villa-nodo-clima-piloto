/* L2 portal — por qué dirección local se atiende el portal (FR-POR-10, SEC-06). Núcleo puro. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

/* IP del AP del portal (FSD §11.1). */
extern const uint8_t PORTAL_IP_AP[4];

/* true solo si la dirección local de la conexión (IPv4, orden de red) es la del AP: en
 * VALIDANDO el nodo también tiene la IP del STA en la red doméstica, y por ahí no se atiende. */
bool portal_origen_permitido(const uint8_t ip_local[4]);
