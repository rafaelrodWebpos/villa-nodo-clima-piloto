/* L2 conectividad — seguridad mínima del STA (FSD FR-CON-07, SEC-07). Núcleo puro. */
#include "conectividad_sta.h"
#include <stddef.h>

con_sta_seguridad_t con_sta_seguridad(const char *wifi_pass)
{
    const bool con_clave = wifi_pass != NULL && wifi_pass[0] != '\0';
    return (con_sta_seguridad_t){
        .umbral = con_clave ? CON_STA_UMBRAL_WPA2_PSK : CON_STA_UMBRAL_ABIERTA,
        .pmf_capaz = true,
        .pmf_requerido = false,
    };
}
