/* L1 portal — servidor DNS cautivo (FR-POR-02). Adaptador de ESP-IDF/lwIP. */
#pragma once
#include "esp_err.h"

/* Arranca una tarea que contesta en UDP/53 toda consulta A con 192.168.4.1. */
/* indice_ap: devuelve el índice lwIP de la interfaz del AP (esp_netif_get_netif_impl_index);
 * se consulta con cada datagrama, porque al abrir el socket en T02 la interfaz puede no estar
 * añadida todavía. Solo se contesta lo que portal_dns_atender admite (FR-POR-10). */
typedef int (*portal_indice_ap_t)(void);
esp_err_t portal_dns_iniciar(portal_indice_ap_t indice_ap);

/* Detiene el DNS cautivo (T24, FR-POR-08). */
void portal_dns_detener(void);
