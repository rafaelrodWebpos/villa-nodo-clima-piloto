/* L1 identidad (FSD §16, FR-ID-01). Núcleo puro: compila sin ESP-IDF. */
#include "identidad.h"
#include <stdio.h>

void identidad_desde_mac(const uint8_t mac[6], char out[IDENTIDAD_LEN])
{
    snprintf(out, IDENTIDAD_LEN, "clima-%02x%02x%02x", mac[3], mac[4], mac[5]);
}
