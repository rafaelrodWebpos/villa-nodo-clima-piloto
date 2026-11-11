/* L1 portal — servidor DNS cautivo (FR-POR-02). Adaptador de ESP-IDF/lwIP. */
#pragma once
#include "esp_err.h"

/* Arranca una tarea que contesta en UDP/53 toda consulta A con 192.168.4.1. */
/* ifname_ap: nombre lwIP de la interfaz del AP (esp_netif_get_netif_impl_name); el socket se
 * liga a ella y a 192.168.4.1 (FR-POR-10). */
esp_err_t portal_dns_iniciar(const char *ifname_ap);

/* Detiene el DNS cautivo (T24, FR-POR-08). */
void portal_dns_detener(void);
