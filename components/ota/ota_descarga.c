/* L1 ota — descarga de la imagen (FSD §7). Adaptador de ESP-IDF; las decisiones son del
 * núcleo puro (ota_politica.c, ota_turno.c). */
#include "ota_descarga.h"
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include "esp_crt_bundle.h"
#include "esp_tls_errors.h"
#include "esp_http_client.h"
#include "esp_https_ota.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "ota_turno.h"

static const char *TAG = "nodo";
#define TIMEOUT_MS 30000              /* FR-OTA-12: 30 s sin datos */
/* §12.1 limita a 512 bytes la URL del comando, no las redirecciones: la URL firmada de
 * release-assets.githubusercontent.com mide ~900 (medida el 2026-11-14) */
#define URL_SALTO_MAX 2048

/* Location de la respuesta, capturada por el manejador de eventos (esp_http_client_get_url
 * reconstruye esquema://host:puerto/ruta y pierde la consulta firmada de GitHub). */
typedef struct { char url[URL_SALTO_MAX]; bool hay, no_cabe; } location_t;

/* A3-03 (H-91): todo lo de una descarga vive en su contexto, propio de su tarea; nada se
 * comparte con una descarga posterior. */
typedef struct {
    char url[OTA_URL_MAX + 1];
    char en_ejecucion[32];
    bool es_prueba, imagen_banco;
    ota_fin_cb_t fin;
    location_t loc;
    char final[URL_SALTO_MAX];
} descarga_t;

static portMUX_TYPE s_cerrojo = portMUX_INITIALIZER_UNLOCKED;
static ota_turno_t s_turno;           /* bajo s_cerrojo */

static bool abortada(void)
{
    taskENTER_CRITICAL(&s_cerrojo);
    bool a = s_turno.abortada;
    taskEXIT_CRITICAL(&s_cerrojo);
    return a;
}

/* B-1: la imagen nueva ya es arrancable pero la descarga se abortó (T22): el arranque vuelve
 * a la partición en ejecución, para que un reinicio posterior no cambie de imagen. */
static void restaurar_arranque(void)
{
    const esp_partition_t *actual = esp_ota_get_running_partition();
    esp_err_t e = actual ? esp_ota_set_boot_partition(actual) : ESP_FAIL;
    ESP_LOGW("ota_descarga", "aborto tras escribir la imagen: arranque devuelto a %s (%s)",
             actual ? actual->label : "?", esp_err_to_name(e));
}

static esp_err_t al_evento_http(esp_http_client_event_t *e)
{
    location_t *loc = e->user_data;
    if (loc && e->event_id == HTTP_EVENT_ON_HEADER && e->header_key && strcasecmp(e->header_key, "Location") == 0) {
        loc->hay = true;
        loc->no_cabe = strlcpy(loc->url, e->header_value, sizeof loc->url) >= sizeof loc->url;
    }
    return ESP_OK;
}

static void config_http(esp_http_client_config_t *c, const char *url, location_t *loc)
{
    *c = (esp_http_client_config_t){
        .url = url,
        .crt_bundle_attach = esp_crt_bundle_attach,     /* FR-OTA-03: bundle de CA; el nombre se comprueba */
        .timeout_ms = TIMEOUT_MS,
        .disable_auto_redirect = true,                  /* cada salto se valida aquí (FR-OTA-02/14) */
        .keep_alive_enable = false,
        .event_handler = al_evento_http,
        .user_data = loc,
        .buffer_size = 2048,                            /* cabeceras de respuesta largas (Location firmada) */
        .buffer_size_tx = URL_SALTO_MAX + 256,          /* la línea de petición lleva la URL firmada (~900 B) */
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

/* Recorre la cadena de redirecciones hasta la URL que responde 2xx; deja en d->final la última. */
static ota_motivo_t resolver(descarga_t *d)
{
    strlcpy(d->final, d->url, sizeof d->final);
    for (int salto = 0;; salto++) {
        if (abortada()) return OTA_ERROR_RED;                                    /* T22 */
        if (salto > 0) {
            ota_motivo_t m = ota_url_redireccion(d->final, salto, d->imagen_banco);   /* A3-02 */
            if (m != OTA_OK) return m;
        }
        esp_http_client_config_t c;
        config_http(&c, d->final, &d->loc);
        esp_http_client_handle_t h = esp_http_client_init(&c);
        if (!h) return OTA_ERROR_RED;
        d->loc.hay = d->loc.no_cabe = false;
        esp_err_t e = esp_http_client_open(h, 0);
        if (e != ESP_OK) { ota_motivo_t m = motivo_conexion(h, e); esp_http_client_cleanup(h); return m; }
        if (esp_http_client_fetch_headers(h) < 0) { esp_http_client_cleanup(h); return OTA_ERROR_RED; }
        int st = esp_http_client_get_status_code(h);
        if (st >= 300 && st < 400) {
            esp_http_client_cleanup(h);
            if (!d->loc.hay || d->loc.no_cabe) return OTA_RECHAZADO_HOST;
            strlcpy(d->final, d->loc.url, sizeof d->final);                      /* se valida al empezar el bucle */
            continue;
        }
        esp_http_client_cleanup(h);
        return ota_clasificar_fallo(OTA_FALLO_HTTP, st);   /* OTA_OK con 2xx; si no, error:http */
    }
}

static ota_motivo_t descargar(descarga_t *d, bool *escrita)
{
    esp_http_client_config_t c;
    config_http(&c, d->final, &d->loc);
    esp_https_ota_config_t oc = {.http_config = &c};
    esp_https_ota_handle_t h = NULL;
    esp_err_t e = esp_https_ota_begin(&oc, &h);
    if (e != ESP_OK) return h ? OTA_ERROR_RED : OTA_ERROR_IMAGEN;
    esp_app_desc_t desc;
    ota_motivo_t m = OTA_OK;
    if (esp_https_ota_get_img_desc(h, &desc) != ESP_OK) m = OTA_ERROR_IMAGEN;
    else m = ota_version(d->en_ejecucion, desc.version, d->es_prueba);       /* FR-OTA-05 */
    int total = esp_https_ota_get_image_size(h), ultimo = -1;
    while (m == OTA_OK) {
        if (abortada()) { esp_https_ota_abort(h); return OTA_ERROR_RED; }      /* T22 */
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
    taskENTER_CRITICAL(&s_cerrojo);
    bool seguir = ota_turno_puede_finalizar(&s_turno);   /* B-1: el aborto, justo antes de finish */
    taskEXIT_CRITICAL(&s_cerrojo);
    if (!seguir) { esp_https_ota_abort(h); return OTA_ERROR_RED; }                 /* T22 */
    e = esp_https_ota_finish(h);                       /* cabecera, chip y SHA-256; marca arrancable */
    *escrita = (e == ESP_OK);
    return e == ESP_OK ? OTA_OK : OTA_ERROR_IMAGEN;
}

static void tarea_descarga(void *arg)
{
    descarga_t *d = arg;
    bool escrita = false;
    ota_motivo_t m = resolver(d);
    if (m == OTA_OK) m = descargar(d, &escrita);
    taskENTER_CRITICAL(&s_cerrojo);
    ota_cierre_t cierre = ota_turno_cerrar(&s_turno, escrita);   /* B-1: decidido bajo el cerrojo */
    taskEXIT_CRITICAL(&s_cerrojo);
    if (cierre == OTA_CIERRE_RESTAURAR) restaurar_arranque();     /* abortada después de finish */
    else if (cierre == OTA_CIERRE_AVISAR && d->fin) d->fin(m);    /* abortada (T22): sin aviso */
    free(d);
    taskENTER_CRITICAL(&s_cerrojo);
    ota_turno_soltar(&s_turno);                        /* A3-03: ahora se admite otra descarga */
    taskEXIT_CRITICAL(&s_cerrojo);
    vTaskDelete(NULL);
}

bool ota_descarga_iniciar(const char *url, bool es_prueba, bool imagen_banco, const char *en_ejecucion,
                          ota_fin_cb_t fin)
{
    descarga_t *d = calloc(1, sizeof *d);
    if (!d) return false;
    strlcpy(d->url, url ? url : "", sizeof d->url);
    strlcpy(d->en_ejecucion, en_ejecucion ? en_ejecucion : "", sizeof d->en_ejecucion);
    d->es_prueba = es_prueba;
    d->imagen_banco = imagen_banco;
    d->fin = fin;
    taskENTER_CRITICAL(&s_cerrojo);
    bool turno = ota_turno_tomar(&s_turno);            /* A3-03: la tarea anterior aún no salió → false */
    taskEXIT_CRITICAL(&s_cerrojo);
    if (!turno) { free(d); return false; }
    /* prioridad por debajo de la medición: NFR-OTA-01 (periodo 60 ± 5 s durante la descarga) */
    if (xTaskCreate(tarea_descarga, "ota", 8192, d, 3, NULL) == pdPASS) return true;
    free(d);
    taskENTER_CRITICAL(&s_cerrojo);
    ota_turno_soltar(&s_turno);
    taskEXIT_CRITICAL(&s_cerrojo);
    return false;
}

void ota_descarga_abortar(void)
{
    taskENTER_CRITICAL(&s_cerrojo);
    ota_aborto_t a = ota_turno_abortar(&s_turno);
    taskEXIT_CRITICAL(&s_cerrojo);
    /* B-1: la tarea ya cerró con la imagen escrita y avisó (ota_ok aún en la cola de main):
     * T22 gana y la imagen nueva deja de ser la de arranque */
    if (a == OTA_ABORTO_TARDE) restaurar_arranque();
}
