/* L2 ota — campo `ota` de `status` (FSD §9.3, FR-MQTT-09). Núcleo puro: guarda el valor,
 * valida que sea de §9.3 y decide si el cambio se publica ya o va en el primer `status`
 * tras T11. El adaptador escribe la línea E7 «ota: estado <valor>» (§18) en cada cambio. */
#pragma once
#include <stdbool.h>

#define OTA_DIAG_MAX 32

typedef struct {
    char valor[OTA_DIAG_MAX];   /* «ninguno» al arrancar */
} ota_diag_t;

typedef enum {
    OTA_DIAG_SIN_CAMBIO,        /* mismo valor: ni E7 ni publicación */
    OTA_DIAG_PUBLICAR_YA,       /* conectado (OPERATIVO): status en ≤ 2 s (FR-MQTT-09) */
    OTA_DIAG_CON_T11,           /* sin conexión: va en el primer status de T11 (FR-MQTT-09, T22) */
    OTA_DIAG_INVALIDO,          /* no es un valor de §9.3: no cambia nada */
} ota_diag_resultado_t;

void ota_diag_iniciar(ota_diag_t *d);
bool ota_diag_valido(const char *valor);
ota_diag_resultado_t ota_diag_cambiar(ota_diag_t *d, const char *valor, bool en_operativo);
