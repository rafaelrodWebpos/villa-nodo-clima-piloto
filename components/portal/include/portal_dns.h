/* L1 portal — servidor DNS cautivo (FR-POR-02). Adaptador de ESP-IDF/lwIP. */
#pragma once
#include "esp_err.h"

/* Arranca una tarea que contesta en UDP/53 toda consulta A con 192.168.4.1. */
esp_err_t portal_dns_iniciar(void);

/* Detiene el DNS cautivo (T24, FR-POR-08). */
void portal_dns_detener(void);
