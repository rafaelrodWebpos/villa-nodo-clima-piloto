/* L2 portal — dirección local permitida (FR-POR-10, SEC-06). Núcleo puro. */
#include "portal_origen.h"
#include <string.h>

const uint8_t PORTAL_IP_AP[4] = {192, 168, 4, 1};

bool portal_origen_permitido(const uint8_t ip_local[4])
{
    return ip_local != NULL && memcmp(ip_local, PORTAL_IP_AP, 4) == 0;
}
