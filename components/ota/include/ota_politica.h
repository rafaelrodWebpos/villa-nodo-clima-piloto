/* L2 ota — política de los comandos OTA (FSD §7, §12). Núcleo puro: payload, URL, versión
 * y clasificación de fallos; el adaptador (Fase 3) descarga y escribe la imagen.
 * Motivos de §9.3: rechazado:<payload|host|ruta|misma_version|version_anterior|ocupado>,
 * error:<redirecciones|tls|imagen|http|red>. */
#pragma once
#include <stdbool.h>
#include <stddef.h>

#define OTA_URL_MAX 512                 /* §12.1: url de 1 a 512 bytes */
#define OTA_REDIRECCIONES_MAX 3         /* FR-OTA-02, D14 */

typedef enum {
    OTA_OK = 0,
    OTA_RECHAZADO_PAYLOAD,      /* FR-OTA-09 */
    OTA_RECHAZADO_HOST,         /* FR-OTA-02, FR-OTA-14 (defecto antes de la ruta) */
    OTA_RECHAZADO_RUTA,         /* FR-OTA-11, FR-OTA-13, FR-OTA-14 (defecto en la ruta) */
    OTA_RECHAZADO_MISMA_VERSION,    /* FR-OTA-05 */
    OTA_RECHAZADO_VERSION_ANTERIOR, /* FR-OTA-05 (anti-downgrade de v*, H-84) */
    OTA_RECHAZADO_OCUPADO,      /* FR-OTA-10 */
    OTA_ERROR_REDIRECCIONES,    /* FR-OTA-02 */
    OTA_ERROR_TLS,              /* FR-OTA-03 */
    OTA_ERROR_IMAGEN,           /* FR-OTA-05 */
    OTA_ERROR_HTTP,             /* FR-OTA-12 */
    OTA_ERROR_RED,              /* FR-OTA-12 */
} ota_motivo_t;

/* Texto de §9.3 («rechazado:host», «error:red»…); «ok» para OTA_OK. */
const char *ota_motivo_texto(ota_motivo_t m);

/* FR-OTA-09: payload JSON {"url":"…"} con exactamente esa clave y una cadena de 1-512
 * bytes. Copia la URL decodificada en url (cap ≥ OTA_URL_MAX + 1). */
ota_motivo_t ota_payload(const char *json, size_t len, char *url, size_t cap);

/* FR-OTA-14 + FR-OTA-02 + FR-OTA-11 + FR-OTA-13, en ese orden, para la URL inicial.
 * imagen_banco: la imagen de banco acepta las pre-releases ota-test-* (FR-OTA-13).
 * *es_prueba = true si la URL es de una pre-release ota-test-* (fuera del anti-downgrade). */
ota_motivo_t ota_url_inicial(const char *url, bool imagen_banco, bool *es_prueba);

/* FR-OTA-14 + FR-OTA-02 para cada redirección (sin la regla de la ruta del repo);
 * saltos = número de redirección (1, 2, 3…); la cuarta es error:redirecciones. */
ota_motivo_t ota_url_redireccion(const char *url, int saltos);

/* FR-OTA-05: versión de la imagen descargada frente a la que corre. es_prueba: pre-release
 * ota-test-* (sin anti-downgrade, H-84). Una versión que no es semver es error:imagen. */
ota_motivo_t ota_version(const char *en_ejecucion, const char *destino, bool es_prueba);

/* FR-OTA-12: clasificación de un fallo de descarga. */
typedef enum { OTA_FALLO_DNS, OTA_FALLO_TCP, OTA_FALLO_TIMEOUT, OTA_FALLO_TLS, OTA_FALLO_HTTP } ota_fallo_t;
ota_motivo_t ota_clasificar_fallo(ota_fallo_t fallo, int estado_http);
