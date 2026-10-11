/*
 * Nodo Clima Piloto — raíz de composición.
 *
 * Esqueleto de la Fase 1 del harness: prueba la tubería (build → artefacto →
 * marcador) y no implementa ningún requisito del FSD. Los componentes llegan
 * con /build, cada uno detrás de su test.
 */
#include "esp_app_desc.h"
#include "esp_log.h"
#include "sdkconfig.h"

static const char *TAG = "nodo";

#if CONFIG_NODO_BENCH_BUILD
/* Marcador que la CI busca en el binario (FSD C-LOG-01). Solo existe en la
 * imagen de banco; la de producción no debe contenerlo. */
static const char BENCH_MARKER[] = "NODO-BENCH-IMAGE";
#endif

void app_main(void)
{
    const esp_app_desc_t *app = esp_app_get_description();
    ESP_LOGI(TAG, "nodo_clima %s", app->version);
#if CONFIG_NODO_BENCH_BUILD
    ESP_LOGI(TAG, "%s", BENCH_MARKER);
#endif
    /* Marcador de arranque del contrato del testbench: última línea de app_main. */
    ESP_LOGI(TAG, "Init complete");
}
