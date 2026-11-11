/* L2 portal — a quién atiende el portal (FR-POR-10, SEC-06). Núcleo puro. */
#include "portal_origen.h"
#include <string.h>

const uint8_t PORTAL_IP_AP[4] = {192, 168, 4, 1};

bool portal_origen_permitido(const uint8_t ip_local[4], const uint8_t ip_remota[4])
{
    if (ip_local == NULL || ip_remota == NULL) return false;
    if (memcmp(ip_local, PORTAL_IP_AP, 4) != 0) return false;              /* dirigida a la IP del AP */
    if (memcmp(ip_remota, PORTAL_IP_AP, 3) != 0) return false;             /* cliente de 192.168.4.0/24 */
    return ip_remota[3] != 0 && ip_remota[3] != 255 && ip_remota[3] != 1;  /* ni red, ni difusión, ni el propio AP */
}
