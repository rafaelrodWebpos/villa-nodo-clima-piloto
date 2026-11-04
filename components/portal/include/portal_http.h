/* L1 portal — servidor HTTP del portal (FSD §11). Adaptador de ESP-IDF. */
#pragma once
#include <stdbool.h>
#include "esp_err.h"

/* Aviso a la raíz de composición de cada envío del formulario, ya validado
 * (evento «envío» de §6.3; valido = guarda de T03/T04). */
typedef void (*portal_envio_cb_t)(bool valido);

/* Arranca el servidor HTTP en el puerto 80: GET / sirve el formulario
 * (FR-POR-03) y POST / lo valida (FR-POR-04). id y version deben vivir
 * mientras viva el servidor. */
esp_err_t portal_http_iniciar(const char *id, const char *version, portal_envio_cb_t al_enviar);
