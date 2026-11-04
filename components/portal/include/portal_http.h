/* L1 portal — servidor HTTP del portal (FSD §11). Adaptador de ESP-IDF. */
#pragma once
#include "esp_err.h"

/* Arranca el servidor HTTP en el puerto 80 (FR-POR-03: GET / sirve el
 * formulario). id y version deben vivir mientras viva el servidor. */
esp_err_t portal_http_iniciar(const char *id, const char *version);
