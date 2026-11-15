/* L2 portal — a quién atiende el portal (FR-POR-10, SEC-06). Núcleo puro. */
#pragma once
#include <stdbool.h>
#include <stdint.h>

/* IP del AP del portal (FSD §11.1) y su red, 192.168.4.0/24. */
extern const uint8_t PORTAL_IP_AP[4];

/* true solo si la conexión llega dirigida a la IP del AP (ip_local) y viene de un cliente de
 * 192.168.4.0/24 (ip_remota), ambas IPv4 en orden de red. lwIP acepta por cualquier interfaz
 * un paquete dirigido a una IP propia (host débil): en VALIDANDO, un equipo de la red
 * doméstica podría llegar a 192.168.4.1 a través del STA; su IP de origen lo delata. */
bool portal_origen_permitido(const uint8_t ip_local[4], const uint8_t ip_remota[4]);

/* DNS cautivo (FR-POR-10, SEC-06): true solo si la consulta llegó dirigida a la IP del AP
 * (destino), entró por la interfaz del AP (if_entrada == if_ap, índices de lwIP > 0) y viene
 * de un cliente de 192.168.4.0/24 (origen). Los datos salen de IP_PKTINFO de cada datagrama. */
bool portal_dns_atender(const uint8_t destino[4], int if_entrada, int if_ap, const uint8_t origen[4]);
