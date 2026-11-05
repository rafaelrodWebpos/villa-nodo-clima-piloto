/* L0 udplog — copia del log por UDP hacia el banco (FSD §18.1). Adaptador.
 * Solo existe con CONFIG_NODO_UDP_LOG=y (imagen de banco); con =n, udplog_iniciar
 * no hace nada y el binario no contiene el envío (FR-LOG-01, C-LOG-01). */
#pragma once
#include "esp_err.h"

/* Engancha el log y prepara el envío. Requiere el bucle de eventos por defecto. */
esp_err_t udplog_iniciar(void);
