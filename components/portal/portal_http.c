/* L1 portal — adaptador HTTP (esp_http_server). Implementado: GET / con el
 * formulario de §17 (FR-POR-03) y POST / con la validación (FR-POR-04, T03).
 * Pendientes, cada uno con su test: la prueba de unión de un envío válido
 * (T04, JRN-01.2) y las redirecciones y el DNS cautivo (FR-POR-02). */
#include <stdlib.h>
#include <string.h>
#include "esp_http_server.h"
#include "esp_log.h"
#include "portal_form.h"
#include "portal_http.h"
#include "portal_textos.h"
#include "portal_urlenc.h"
#include "portal_validar.h"

#define HTML_MAX 8192
#define BODY_MAX 1024      /* 8 campos de §17 con sus máximos, urlencoded, caben con holgura */

static const char *TAG = "portal";
static const char *s_id, *s_version;
static portal_envio_cb_t s_al_enviar;

static esp_err_t enviar_html(httpd_req_t *req, const char *html, size_t n)
{
    httpd_resp_set_type(req, "text/html; charset=utf-8");
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    return httpd_resp_send(req, html, (ssize_t)n);
}

static esp_err_t get_raiz(httpd_req_t *req)
{
    char *html = malloc(HTML_MAX);
    if (!html) return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, NULL);
    portal_form_t f = {.id = s_id, .version = s_version};
    size_t n = portal_form_html(html, HTML_MAX, &f);
    esp_err_t r = n ? enviar_html(req, html, n) : httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, NULL);
    free(html);
    return r;
}

static esp_err_t post_raiz(httpd_req_t *req)
{
    if (req->content_len > BODY_MAX)
        return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, NULL);
    char *body = malloc(BODY_MAX + 1);
    char *html = malloc(HTML_MAX);
    esp_err_t r = ESP_OK;
    if (!body || !html) { r = httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, NULL); goto fin; }
    size_t leido = 0;
    while (leido < req->content_len) {
        int n = httpd_req_recv(req, body + leido, req->content_len - leido);
        if (n == HTTPD_SOCK_ERR_TIMEOUT) continue;
        if (n <= 0) { r = ESP_FAIL; goto fin; }
        leido += (size_t)n;
    }
    body[leido] = '\0';

    const char *v[PORTAL_N_CAMPOS];
    portal_decodificar(body, v);
    portal_validacion_t val;
    portal_validar(v, &val);
    if (s_al_enviar) s_al_enviar(val.n_errores == 0);

    size_t n;
    if (val.n_errores) {
        /* T03: el formulario con el error de cada campo; la NVS no se toca */
        portal_form_t f = {.id = s_id, .version = s_version};
        memcpy(f.valores, v, sizeof f.valores);
        memcpy(f.error, val.error, sizeof f.error);
        n = portal_form_html(html, HTML_MAX, &f);
    } else {
        /* T04 llega con JRN-01.2: por ahora, aviso temporal y nada se guarda */
        n = portal_mensaje_html(html, HTML_MAX, s_id, s_version, TX_PENDIENTE);
    }
    r = n ? enviar_html(req, html, n) : httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, NULL);
fin:
    free(body);
    free(html);
    return r;
}

esp_err_t portal_http_iniciar(const char *id, const char *version, portal_envio_cb_t al_enviar)
{
    s_id = id;
    s_version = version;
    s_al_enviar = al_enviar;
    httpd_handle_t srv = NULL;
    httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
    esp_err_t err = httpd_start(&srv, &cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "httpd_start: %s", esp_err_to_name(err));
        return err;
    }
    static const httpd_uri_t raiz_get = {.uri = "/", .method = HTTP_GET, .handler = get_raiz};
    static const httpd_uri_t raiz_post = {.uri = "/", .method = HTTP_POST, .handler = post_raiz};
    ESP_ERROR_CHECK(httpd_register_uri_handler(srv, &raiz_get));
    return httpd_register_uri_handler(srv, &raiz_post);
}
