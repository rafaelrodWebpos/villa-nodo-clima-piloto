/* L1 portal — servidor HTTP del portal (FSD §11). Adaptador de ESP-IDF. */
#pragma once
#include <stdbool.h>
#include "esp_err.h"
#include "portal_form.h"

/* Qué responde el portal a un envío, según la fila de §6.3 que lo trató. */
typedef enum {
    PORTAL_RESP_ERRORES,    /* T03: el formulario con el error de cada campo */
    PORTAL_RESP_PROBANDO,   /* T04: «Probando la conexión…» */
    PORTAL_RESP_OCUPADO,    /* T07: «ocupado» */
} portal_resp_t;

/* Lo que muestra GET / (sigue al estado del gestor de conectividad). */
typedef enum {
    PORTAL_VISTA_FORMULARIO,
    PORTAL_VISTA_PROBANDO,      /* VALIDANDO */
    PORTAL_VISTA_NO_CONECTA,    /* tras T06 (FR-POR-05) */
    PORTAL_VISTA_CONECTADO,     /* tras T05, hasta el reinicio */
} portal_vista_t;

/* Aviso a la raíz de composición de cada envío, ya decodificado y validado
 * (evento «envío» de §6.3; valido = guarda de T03/T04). Los valores solo
 * viven durante la llamada. */
typedef portal_resp_t (*portal_envio_cb_t)(const char *const v[PORTAL_N_CAMPOS], bool valido);

/* Arranca el servidor HTTP en el puerto 80. id y version deben vivir mientras
 * viva el servidor. */
esp_err_t portal_http_iniciar(const char *id, const char *version, portal_envio_cb_t al_enviar);

/* Cambia lo que muestra GET / (T05, T06). */
void portal_http_vista(portal_vista_t v);
