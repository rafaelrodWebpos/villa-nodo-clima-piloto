/* L1 ota — descarga de la imagen (FSD §7). Adaptador de ESP-IDF; las decisiones son del
 * núcleo puro (ota_politica.c). */
#include "ota_descarga.h"
#include <string.h>
#include "esp_crt_bundle.h"
#include "esp_tls_errors.h"
#include "esp_http_client.h"
#include "esp_https_ota.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "nodo";
#define TIMEOUT_MS 30000              /* FR-OTA-12: 30 s sin datos */

static char s_url[OTA_URL_MAX + 1];
static char s_en_ejecucion[32];
static bool s_es_prueba;
static ota_fin_cb_t s_fin;
static volatile bool s_abortar;

static void config_http(esp_http_client_config_t *c, const char *url)
{
    *c = (esp_http_client_config_t){
        .url = url,
        .crt_bundle_attach = esp_crt_bundle_attach,     /* FR-OTA-03: bundle de CA; el nombre se comprueba */
        .timeout_ms = TIMEOUT_MS,
        .disable_auto_redirect = true,                  /* cada salto se valida aquí (FR-OTA-02/14) */
        .keep_alive_enable = false,
    };
}

/* Fallo de conexión → motivo (FR-OTA-12 / FR-OTA-03) a partir del error de esp-tls. */
static ota_motivo_t motivo_conexion(esp_http_client_handle_t h, esp_err_t e)
{
    int codigo = 0, flags = 0;
    esp_err_t tls = esp_http_client_get_and_clear_last_tls_error(h, &codigo, &flags);
    if (flags != 0 || tls == ESP_ERR_MBEDTLS_SSL_HANDSHAKE_FAILED) return ota_clasificar_fallo(OTA_FALLO_TLS, 0);
    if (tls == ESP_ERR_ESP_TLS_CANNOT_RESOLVE_HOSTNAME) return ota_clasificar_fallo(OTA_FALLO_DNS, 0);
    if (e == ESP_ERR_HTTP_EAGAIN || e == ESP_ERR_TIMEOUT) return ota_clasificar_fallo(OTA_FALLO_TIMEOUT, 0);
    return ota_clasificar_fallo(OTA_FALLO_TCP, 0);
}

/* Recorre la cadena de redirecciones hasta la URL que responde 2xx; deja en final la última. */
static ota_motivo_t resolver(char *final, size_t cap)
{
    strlcpy(final, s_url, cap);
    for (int salto = 0;; salto++) {
        if (salto > 0) {
            ota_motivo_t m = ota_url_redireccion(final, salto);
            if (m != OTA_OK) return m;
        }
        esp_http_client_config_t c;
        config_http(&c, final);
        esp_http_client_handle_t h = esp_http_client_init(&c);
        if (!h) return OTA_ERROR_RED;
        esp_err_t e = esp_http_client_open(h, 0);
        if (e != ESP_OK) { ota_motivo_t m = motivo_conexion(h, e); esp_http_client_cleanup(h); return m; }
        if (esp_http_client_fetch_headers(h) < 0) { esp_http_client_cleanup(h); return OTA_ERROR_RED; }
        int st = esp_http_client_get_status_code(h);
        if (st >= 300 && st < 400) {
            char *loc = NULL;
            if (esp_http_client_get_header(h, "Location", &loc) != ESP_OK || !loc || strlen(loc) >= cap) {
                esp_http_client_cleanup(h);
                return OTA_RECHAZADO_HOST;
            }
            strlcpy(final, loc, cap);
            esp_http_client_cleanup(h);
            continue;
        }
        esp_http_client_cleanup(h);
        return ota_clasificar_fallo(OTA_FALLO_HTTP, st);   /* OTA_OK con 2xx; si no, error:http */
    }
}

static ota_motivo_t descargar(const char *url)
{
    esp_http_client_config_t c;
    config_http(&c, url);
    esp_https_ota_config_t oc = {.http_config = &c};
    esp_https_ota_handle_t h = NULL;
    esp_err_t e = esp_https_ota_begin(&oc, &h);
    if (e != ESP_OK) return h ? OTA_ERROR_RED : OTA_ERROR_IMAGEN;
    esp_app_desc_t desc;
    ota_motivo_t m = OTA_OK;
    if (esp_https_ota_get_img_desc(h, &desc) != ESP_OK) m = OTA_ERROR_IMAGEN;
    else m = ota_version(s_en_ejecucion, desc.version, s_es_prueba);           /* FR-OTA-05 */
    int total = esp_https_ota_get_image_size(h), ultimo = -1;
    while (m == OTA_OK) {
        if (s_abortar) { esp_https_ota_abort(h); return OTA_ERROR_RED; }      /* T22 */
        e = esp_https_ota_perform(h);
        if (total > 0) {
            int pct = (int)(100LL * esp_https_ota_get_image_len_read(h) / total) / 10 * 10;
            if (pct != ultimo) { ESP_LOGI(TAG, "ota: %d %%", pct); ultimo = pct; }   /* §18 */
        }
        if (e == ESP_ERR_HTTPS_OTA_IN_PROGRESS) continue;
        if (e != ESP_OK) m = (e == ESP_ERR_OTA_VALIDATE_FAILED) ? OTA_ERROR_IMAGEN : OTA_ERROR_RED;
        break;
    }
    if (m != OTA_OK) { esp_https_ota_abort(h); return m; }
    if (!esp_https_ota_is_complete_data_received(h)) { esp_https_ota_abort(h); return OTA_ERROR_IMAGEN; }
    e = esp_https_ota_finish(h);                       /* cabecera, chip y SHA-256; marca arrancable */
    return e == ESP_OK ? OTA_OK : OTA_ERROR_IMAGEN;
}

static void tarea_descarga(void *arg)
{
    static char final[OTA_URL_MAX + 1];
    ota_motivo_t m = resolver(final, sizeof final);
    if (m == OTA_OK) m = descargar(final);
    if (!s_abortar && s_fin) s_fin(m);
    vTaskDelete(NULL);
}

bool ota_descarga_iniciar(const char *url, bool es_prueba, const char *en_ejecucion, ota_fin_cb_t fin)
{
    strlcpy(s_url, url, sizeof s_url);
    strlcpy(s_en_ejecucion, en_ejecucion ? en_ejecucion : "", sizeof s_en_ejecucion);
    s_es_prueba = es_prueba;
    s_fin = fin;
    s_abortar = false;
    /* prioridad por debajo de la medición: NFR-OTA-01 (periodo 60 ± 5 s durante la descarga) */
    return xTaskCreate(tarea_descarga, "ota", 8192, NULL, 3, NULL) == pdPASS;
}

void ota_descarga_abortar(void)
{
    s_abortar = true;
}
