/* L1 portal — adaptador HTTP (esp_http_server): GET / según la vista (el
 * formulario de §17, «Probando la conexión…», «No se pudo conectar…» o
 * «Conectado…»), POST / con la validación y la respuesta de T03/T04/T07, y 302
 * a http://192.168.4.1/ para cualquier otra ruta GET (FR-POR-02..06). */
#include <stdlib.h>
#include <string.h>
#include "esp_http_server.h"
#include "esp_log.h"
#include "portal_cautivo.h"
#include "portal_form.h"
#include "portal_lectura.h"
#include "portal_http.h"
#include "portal_textos.h"
#include "portal_urlenc.h"
#include "portal_validar.h"

#define HTML_MAX 8192
#define REFRESCO_S 1   /* «Probando…» se recarga cada segundo: «Conectado…» dura poco (T05) */
#define BODY_MAX 1024      /* 8 campos de §17 con sus máximos, urlencoded, caben con holgura */

static const char *TAG = "portal";
static const char *s_id, *s_version;
static portal_envio_cb_t s_al_enviar;
static volatile portal_vista_t s_vista = PORTAL_VISTA_FORMULARIO;
static httpd_handle_t s_srv;

/* Valores no secretos del último envío válido, para volver a mostrarlos tras
 * T06 (FR-POR-05). Los secretos no se guardan aquí nunca. */
static char s_ultimo[PORTAL_N_CAMPOS][65];

void portal_http_vista(portal_vista_t v) { s_vista = v; }

static int es_secreto(int i) { return i == PORTAL_WIFI_PASS || i == PORTAL_MQTT_PASS; }

/* Una línea por respuesta: «portal: <GET|POST> <ruta> -> <página>», sin datos
 * del formulario (la ruta pasa por portal_ruta_log, TC-SEC-02). Sirve para
 * saber qué vio el teléfono en cada momento. */
static void log_pagina(httpd_req_t *req, const char *pagina)
{
    char ruta[41];
    portal_ruta_log(req->uri, ruta, sizeof ruta);
    ESP_LOGI(TAG, "%s %s -> %s", req->method == HTTP_POST ? "POST" : "GET", ruta, pagina);
}

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
    size_t n;
    const char *pagina;
    switch (s_vista) {
    case PORTAL_VISTA_PROBANDO:
        pagina = "probando";
        n = portal_mensaje_html(html, HTML_MAX, s_id, s_version, TX_PROBANDO, "estado-probando", REFRESCO_S);
        break;
    case PORTAL_VISTA_CONECTADO:
        pagina = "conectado";
        n = portal_mensaje_html(html, HTML_MAX, s_id, s_version, TX_CONECTADO, "estado-conectado", 0);
        break;
    case PORTAL_VISTA_NO_CONECTA: {
        pagina = "no-conecta";
        portal_form_t f = {.id = s_id, .version = s_version, .aviso = TX_NO_CONECTA, .aviso_id = "no-conecta"};
        for (int i = 0; i < PORTAL_N_CAMPOS; i++) if (!es_secreto(i)) f.valores[i] = s_ultimo[i];
        n = portal_form_html(html, HTML_MAX, &f);
        break;
    }
    default: {
        pagina = "formulario";
        portal_form_t f = {.id = s_id, .version = s_version};
        n = portal_form_html(html, HTML_MAX, &f);
    }
    }
    log_pagina(req, pagina);
    esp_err_t r = n ? enviar_html(req, html, n) : httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, NULL);
    free(html);
    return r;
}

/* FR-POR-02: /generate_204, /hotspot-detect.html y cualquier otra ruta GET -> 302 al portal */
static esp_err_t get_otra(httpd_req_t *req)
{
    if (!portal_redirige(req->uri)) return get_raiz(req);
    log_pagina(req, "302");
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", PORTAL_URL);
    httpd_resp_set_hdr(req, "Cache-Control", "no-store");
    return httpd_resp_send(req, NULL, 0);
}

static esp_err_t post_raiz(httpd_req_t *req)
{
    if (req->content_len > BODY_MAX)
        return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, NULL);
    char *body = malloc(BODY_MAX + 1);
    char *html = malloc(HTML_MAX);
    esp_err_t r = ESP_OK;
    if (!body || !html) { r = httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, NULL); goto fin; }
    /* FR-POR-09 (SEC-05): sin límite, un cliente que declara el cuerpo y no lo manda
     * retendría la tarea del servidor; a la tercera espera seguida, 408 y se corta */
    size_t leido = 0;
    int esperas = 0;
    while (leido < req->content_len) {
        int n = httpd_req_recv(req, body + leido, req->content_len - leido);
        switch (portal_lectura_paso(n, n == HTTPD_SOCK_ERR_TIMEOUT, &esperas)) {
        case PORTAL_LECTURA_DATOS:   leido += (size_t)n; break;
        case PORTAL_LECTURA_ESPERAR: break;
        case PORTAL_LECTURA_408:
            log_pagina(req, "408");
            httpd_resp_send_err(req, HTTPD_408_REQ_TIMEOUT, NULL);
            r = ESP_FAIL;                          /* ESP_FAIL: el servidor cierra la conexión */
            goto fin;
        case PORTAL_LECTURA_CORTAR:  r = ESP_FAIL; goto fin;
        }
    }
    body[leido] = '\0';

    const char *v[PORTAL_N_CAMPOS];
    portal_decodificar(body, v);
    portal_validacion_t val;
    portal_validar(v, &val);
    portal_resp_t resp = s_al_enviar ? s_al_enviar(v, val.n_errores == 0) : PORTAL_RESP_ERRORES;

    size_t n;
    if (resp == PORTAL_RESP_PROBANDO) {
        /* T04: se responde enseguida y la página se recarga hasta el resultado */
        for (int i = 0; i < PORTAL_N_CAMPOS; i++) {
            s_ultimo[i][0] = '\0';
            if (!es_secreto(i) && v[i]) strlcpy(s_ultimo[i], v[i], sizeof s_ultimo[i]);
        }
        s_vista = PORTAL_VISTA_PROBANDO;
        log_pagina(req, "probando");
        n = portal_mensaje_html(html, HTML_MAX, s_id, s_version, TX_PROBANDO, "estado-probando", REFRESCO_S);
    } else if (resp == PORTAL_RESP_OCUPADO) {
        log_pagina(req, "ocupado");
        n = portal_mensaje_html(html, HTML_MAX, s_id, s_version, TX_OCUPADO, "estado-ocupado", REFRESCO_S);
    } else {
        log_pagina(req, "errores");
        /* T03: el formulario con el error de cada campo; la NVS no se toca */
        portal_form_t f = {.id = s_id, .version = s_version};
        memcpy(f.valores, v, sizeof f.valores);
        memcpy(f.error, val.error, sizeof f.error);
        n = portal_form_html(html, HTML_MAX, &f);
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
    cfg.lru_purge_enable = true;                   /* SEC-05: con todos los huecos ocupados, se cierra la conexión más antigua */
    cfg.uri_match_fn = httpd_uri_match_wildcard;   /* el comodín recoge las rutas de detección */
    esp_err_t err = httpd_start(&srv, &cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "httpd_start: %s", esp_err_to_name(err));
        return err;
    }
    static const httpd_uri_t raiz_get = {.uri = "/", .method = HTTP_GET, .handler = get_raiz};
    static const httpd_uri_t raiz_post = {.uri = "/", .method = HTTP_POST, .handler = post_raiz};
    static const httpd_uri_t otra_get = {.uri = "/*", .method = HTTP_GET, .handler = get_otra};
    /* Orden: «/» exacta antes que el comodín */
    ESP_ERROR_CHECK(httpd_register_uri_handler(srv, &raiz_get));
    ESP_ERROR_CHECK(httpd_register_uri_handler(srv, &raiz_post));
    s_srv = srv;
    return httpd_register_uri_handler(srv, &otra_get);
}

void portal_http_detener(void)
{
    if (s_srv) { httpd_stop(s_srv); s_srv = NULL; }
}
