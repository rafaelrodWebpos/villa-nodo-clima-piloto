/* L2 ota — campo `ota` de `status` (FSD §9.3, FR-MQTT-09). Núcleo puro. */
#include "ota_diag.h"
#include <string.h>

static const char *const VALIDOS[] = {
    "ninguno", "en_curso", "ok",
    "rechazado:payload", "rechazado:host", "rechazado:ruta", "rechazado:misma_version",
    "rechazado:version_anterior", "rechazado:ocupado",
    "error:redirecciones", "error:tls", "error:imagen", "error:http", "error:red",
};

void ota_diag_iniciar(ota_diag_t *d)
{
    strcpy(d->valor, "ninguno");
}

bool ota_diag_valido(const char *valor)
{
    if (!valor) return false;
    for (size_t i = 0; i < sizeof VALIDOS / sizeof VALIDOS[0]; i++)
        if (strcmp(valor, VALIDOS[i]) == 0) return true;
    return false;
}

ota_diag_resultado_t ota_diag_cambiar(ota_diag_t *d, const char *valor, bool en_operativo)
{
    if (!ota_diag_valido(valor)) return OTA_DIAG_INVALIDO;
    if (strcmp(d->valor, valor) == 0) return OTA_DIAG_SIN_CAMBIO;
    strcpy(d->valor, valor);                 /* cabe: el más largo de §9.3 tiene 26 caracteres */
    return en_operativo ? OTA_DIAG_PUBLICAR_YA : OTA_DIAG_CON_T11;
}
