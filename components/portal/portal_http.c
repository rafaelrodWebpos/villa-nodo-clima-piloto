/* L1 portal — adaptador HTTP (esp_http_server). Implementado: GET / con el
 * formulario de §17 (FR-POR-03). Pendientes, cada uno con su test: POST /
 * (FR-POR-04, T03/T04) y las redirecciones y el DNS cautivo (FR-POR-02). */
#include <stdlib.h>
#include "esp_http_server.h"
#include "esp_log.h"
#include "portal_form.h"
#include "portal_http.h"

#define HTML_MAX 8192

static const char *TAG = "portal";
static const char *s_id, *s_version;

static esp_err_t get_raiz(httpd_req_t *req)
{
    char *html = malloc(HTML_MAX);
    if (!html) return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, NULL);
    portal_form_t f = {.id = s_id, .version = s_version};
    size_t n = portal_form_html(html, HTML_MAX, &f);
    esp_err_t r;
    if (n == 0) {
        r = httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, NULL);
    } else {
        httpd_resp_set_type(req, "text/html; charset=utf-8");
        httpd_resp_set_hdr(req, "Cache-Control", "no-store");
        r = httpd_resp_send(req, html, (ssize_t)n);
    }
    free(html);
    return r;
}

esp_err_t portal_http_iniciar(const char *id, const char *version)
{
    s_id = id;
    s_version = version;
    httpd_handle_t srv = NULL;
    httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
    esp_err_t err = httpd_start(&srv, &cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "httpd_start: %s", esp_err_to_name(err));
        return err;
    }
    static const httpd_uri_t raiz = {.uri = "/", .method = HTTP_GET, .handler = get_raiz};
    return httpd_register_uri_handler(srv, &raiz);
}
