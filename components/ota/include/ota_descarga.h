/* L1 ota — descarga de la imagen (FSD §7, T17/T19/T20/T22). Adaptador de ESP-IDF: recorre
 * las redirecciones a mano validando cada salto con la política pura (FR-OTA-02/14, máx. 3),
 * descarga con esp_https_ota y el bundle de CA (FR-OTA-03), comprueba la versión antes de
 * escribir (FR-OTA-05) y escribe «ota: <n> %» (§18). El resultado llega por `fin`, desde la
 * tarea de la descarga: OTA_OK (imagen escrita y arrancable: T19) o el motivo de T20. */
#pragma once
#include <stdbool.h>
#include "ota_politica.h"

typedef void (*ota_fin_cb_t)(ota_motivo_t motivo);

/* Arranca la tarea de la descarga. en_ejecucion: versión de la imagen que corre;
 * imagen_banco: las redirecciones a github.com siguen FR-OTA-13 como la URL inicial (A3-02).
 * false si no se puede: entre otros casos, mientras la tarea de una descarga abortada no
 * haya salido (A3-03; main lo trata como T20 con error:red). */
bool ota_descarga_iniciar(const char *url, bool es_prueba, bool imagen_banco, const char *en_ejecucion,
                          ota_fin_cb_t fin);

/* T22: aborta la descarga en curso sin cambiar la imagen arrancable; `fin` no se llama.
 * La tarea sale en cuanto vuelve de la operación de red en curso (como mucho 30 s). */
void ota_descarga_abortar(void);
