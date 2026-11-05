/*
 * Nodo Clima Piloto — raíz de composición.
 *
 * Crea los adaptadores y conecta los núcleos puros (components/). Implementado
 * hasta ahora: identidad (FR-ID-01), línea boot: (E1), lectura de la
 * configuración (E2) y filas T02–T07 de la tabla: el portal (AP abierto, DNS
 * cautivo, HTTP, validación del envío) y la prueba de unión con su resultado
 * (guardar y reiniciar, o «no se pudo conectar»). Pendiente, cada uno con su
 * test: T01 (arrancar el STA), ciclo de medición (FR-MED-*) y el resto de §6.3.
 */
#include <string.h>
#include "esp_app_desc.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_ota_ops.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "sdkconfig.h"

#include "conectividad.h"
#include "identidad.h"
#include "portal_config.h"
#include "portal_dns.h"
#include "portal_http.h"
#include "portal_validar.h"

static const char *TAG = "nodo";
static char s_id[IDENTIDAD_LEN];
static const char *s_version;

/* Estado del gestor. Lo cambian el arranque, el servidor HTTP y los eventos
 * Wi-Fi (tareas distintas): toda transición pasa por s_lock. */
static con_estado_t s_estado = CON_ARRANQUE;
static SemaphoreHandle_t s_lock;

static portal_config_t s_pendiente;            /* datos del envío en prueba (T04..T06) */
static const char *const *s_envio;             /* valores del envío, solo durante al_enviar */
static esp_timer_handle_t s_t_validacion;      /* T06: 20 s sin IP */
static esp_timer_handle_t s_t_reinicio;        /* T05: reinicio tras responder */
static esp_timer_handle_t s_t_reintento;       /* T04: reintento de la unión dentro de los 20 s */

#define VALIDACION_US   (20 * 1000 * 1000)     /* T06, D12: 20 s */
#define REINICIO_US     (4 * 1000 * 1000)      /* T05: ≤ 5 s desde la línea con: (D12); 4 s para que el teléfono vea «Conectado…» (H-41) */
#define REINTENTO_US    (1 * 1000 * 1000)

#if CONFIG_NODO_BENCH_BUILD
/* Marcador que la CI busca en el binario (FSD C-LOG-01). Solo existe en la
 * imagen de banco; la de producción no debe contenerlo. */
static const char BENCH_MARKER[] = "NODO-BENCH-IMAGE";
#endif

static void ejecutar(con_estado_t origen, con_evento_t ev, con_transicion_t t);

/* Aplica la fila de §6.3 que corresponda a (estado, evento); sin fila, nada. */
static con_transicion_t transicion(con_evento_t ev, con_guardas_t g)
{
    xSemaphoreTakeRecursive(s_lock, portMAX_DELAY);
    con_estado_t origen = s_estado;
    con_transicion_t t = con_transicion(origen, ev, g);
    if (t.fila) {
        s_estado = t.siguiente;   /* antes de la acción: un evento de la acción ya ve el estado nuevo */
        ejecutar(origen, ev, t);
    }
    xSemaphoreGiveRecursive(s_lock);
    return t;
}

/* Valores de `reset` de §9.3. */
static const char *causa_reset(void)
{
    switch (esp_reset_reason()) {
    case ESP_RST_POWERON:  return "poweron";
    case ESP_RST_SW:       return "sw";
    case ESP_RST_PANIC:    return "panic";
    case ESP_RST_TASK_WDT: return "task_wdt";
    case ESP_RST_INT_WDT:  return "int_wdt";
    case ESP_RST_BROWNOUT: return "brownout";
    default:               return "otro";
    }
}

/* E1: «boot: <nodo> fw=<versión> reset=<causa> part=<slot> img=<pendiente|valida>» */
static void log_boot(const char *version)
{
    const esp_partition_t *part = esp_ota_get_running_partition();
    esp_ota_img_states_t st = ESP_OTA_IMG_VALID;
    bool pendiente = esp_ota_get_state_partition(part, &st) == ESP_OK &&
                     st == ESP_OTA_IMG_PENDING_VERIFY;
    ESP_LOGI(TAG, "boot: %s fw=%s reset=%s part=%s img=%s", s_id, version,
             causa_reset(), part->label, pendiente ? "pendiente" : "valida");
}

/* Guarda de T01/T02: hay un registro de configuración en la NVS (espacio
 * «nodo», blob «cfg») y sus campos cumplen §17. Con uno válido escribe E2. */
static bool config_valida(void)
{
    nvs_handle_t h;
    if (nvs_open("nodo", NVS_READONLY, &h) != ESP_OK) return false;
    portal_config_t c;
    size_t len = sizeof c;
    bool leida = nvs_get_blob(h, "cfg", &c, &len) == ESP_OK && len == sizeof c &&
                 c.version == PORTAL_CONFIG_VERSION;
    nvs_close(h);
    if (!leida) return false;
    char puerto[6];
    const char *v[PORTAL_N_CAMPOS];
    portal_config_valores(&c, puerto, v);
    portal_validacion_t val;
    portal_validar(v, &val);
    if (val.n_errores) return false;
    ESP_LOGI(TAG, "cfg: sitio=%s zona=%s", c.sitio, c.zona);   /* E2 */
    memset(&c, 0, sizeof c);                                    /* sin secretos en la pila */
    return true;
}

/* T05: escritura atómica del registro (un solo blob y commit). */
static bool persistir(const portal_config_t *c)
{
    nvs_handle_t h;
    if (nvs_open("nodo", NVS_READWRITE, &h) != ESP_OK) return false;
    bool ok = nvs_set_blob(h, "cfg", c, sizeof *c) == ESP_OK && nvs_commit(h) == ESP_OK;
    nvs_close(h);
    return ok;
}

/* Evento «envío» del portal (tarea del servidor HTTP). */
static portal_resp_t al_enviar(const char *const v[PORTAL_N_CAMPOS], bool valido)
{
    xSemaphoreTakeRecursive(s_lock, portMAX_DELAY);
    s_envio = v;
    con_transicion_t t = transicion(CON_EV_ENVIO, (con_guardas_t){.envio_valido = valido});
    s_envio = NULL;
    xSemaphoreGiveRecursive(s_lock);
    switch (t.accion) {
    case CON_ACC_PROBAR_UNION:      return PORTAL_RESP_PROBANDO;
    case CON_ACC_RESPONDER_OCUPADO: return PORTAL_RESP_OCUPADO;
    default:                        return PORTAL_RESP_ERRORES;
    }
}

/* Eventos Wi-Fi e IP (tarea de eventos) y temporizadores. Fuera de VALIDANDO
 * la tabla aún no tiene fila para ellos y no hacen nada.
 *
 * En VALIDANDO, un intento de unión fallido no es todavía wifi_down: FR-POR-05
 * da 20 s para obtener IP, así que se reintenta cada segundo y T06 llega al
 * vencer la ventana. Así sobrevive a un AP que tarda en aparecer (el banco,
 * de un solo radio, lo levanta después del envío) o a un rechazo puntual.
 * Interpretación aprobada por el propietario (H-41); el FSD no cambia. */
static void al_evento(void *arg, esp_event_base_t base, int32_t id, void *datos)
{
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        xSemaphoreTakeRecursive(s_lock, portMAX_DELAY);
        bool validando = s_estado == CON_VALIDANDO;
        xSemaphoreGiveRecursive(s_lock);
        if (validando) esp_timer_start_once(s_t_reintento, REINTENTO_US);
        else transicion(CON_EV_WIFI_DOWN, (con_guardas_t){0});
    } else if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        transicion(CON_EV_WIFI_UP, (con_guardas_t){0});
    }
}

static void al_reintentar(void *arg)
{
    xSemaphoreTakeRecursive(s_lock, portMAX_DELAY);
    if (s_estado == CON_VALIDANDO) esp_wifi_connect();
    xSemaphoreGiveRecursive(s_lock);
}

static void al_vencer_validacion(void *arg)
{
    transicion(CON_EV_WIFI_DOWN, (con_guardas_t){0});   /* «20 s sin IP» cuenta como wifi_down (T06) */
}

static void al_reiniciar(void *arg)
{
    esp_restart();
}

/* Vuelve a solo AP tras la prueba; el AP del portal no se apaga nunca (T06). */
static void soltar_sta(void)
{
    esp_wifi_disconnect();
    esp_wifi_set_mode(WIFI_MODE_AP);
}

/* Acción de T04: prueba de unión STA (AP+STA) con los datos del formulario. */
static void probar_union(void)
{
    static bool sta_creado;
    if (portal_config_desde(s_envio, &s_pendiente) != 0) {   /* validado: no debería ocurrir */
        ESP_LOGE(TAG, "portal: envío válido que no cabe en el registro");
        esp_timer_start_once(s_t_validacion, 1);            /* sale por T06 */
        return;
    }
    if (!sta_creado) { esp_netif_create_default_wifi_sta(); sta_creado = true; }
    wifi_config_t sta = {0};
    memcpy(sta.sta.ssid, s_pendiente.wifi_ssid, strlen(s_pendiente.wifi_ssid));
    memcpy(sta.sta.password, s_pendiente.wifi_pass, strlen(s_pendiente.wifi_pass));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta));
    memset(&sta, 0, sizeof sta);
    esp_timer_start_once(s_t_validacion, VALIDACION_US);
    esp_wifi_connect();
}

/* Acción de T05: persistir, responder con éxito y reiniciar. */
static void persistir_y_reiniciar(void)
{
    esp_timer_stop(s_t_validacion);
    esp_timer_stop(s_t_reintento);
    if (!persistir(&s_pendiente)) {
        /* Sin persistir no se reinicia (T05, «No debe ocurrir»): fuera de la tabla, se vuelve a PORTAL */
        ESP_LOGE(TAG, "nvs: no se pudo escribir la configuración");
        memset(&s_pendiente, 0, sizeof s_pendiente);
        soltar_sta();
        s_estado = CON_PORTAL;
        portal_http_vista(PORTAL_VISTA_NO_CONECTA);
        return;
    }
    ESP_LOGI(TAG, "nvs: config escrita");                     /* E10 */
    memset(&s_pendiente, 0, sizeof s_pendiente);
    /* Se suelta el STA: el AP del banco también usa 192.168.4.x, y con las dos
     * interfaces activas la respuesta al teléfono podría salir por la del STA */
    soltar_sta();
    portal_http_vista(PORTAL_VISTA_CONECTADO);
    esp_timer_start_once(s_t_reinicio, REINICIO_US);
}

/* Acción de T06: «no se pudo conectar» y descartar los datos. */
static void no_conecta(void)
{
    esp_timer_stop(s_t_validacion);
    esp_timer_stop(s_t_reintento);
    memset(&s_pendiente, 0, sizeof s_pendiente);
    soltar_sta();
    portal_http_vista(PORTAL_VISTA_NO_CONECTA);
}

/* Opción DNS del servidor DHCP del AP (OFFER_DNS de lwip dhcpserver.h; el
 * ejemplo wifi/softap_sta de ESP-IDF la define igual). */
#define DHCPS_OFFER_DNS 0x02

/* Acción de T02 (parte implementada): AP Wi-Fi abierto con SSID = id (FR-POR-01),
 * DNS cautivo anunciado por DHCP (FR-POR-02) y servidor HTTP (FR-POR-02..06). */
static void arrancar_portal(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_t *ap_netif = esp_netif_create_default_wifi_ap();
    /* FR-POR-02: el DHCP del AP anuncia 192.168.4.1 como DNS, para que el
     * teléfono pregunte al nodo y su detección de portal llegue aquí */
    esp_netif_dns_info_t dns = {.ip = {.type = ESP_IPADDR_TYPE_V4, .u_addr.ip4.addr = ESP_IP4TOADDR(192, 168, 4, 1)}};
    uint8_t oferta = DHCPS_OFFER_DNS;
    ESP_ERROR_CHECK_WITHOUT_ABORT(esp_netif_dhcps_stop(ap_netif));
    ESP_ERROR_CHECK(esp_netif_dhcps_option(ap_netif, ESP_NETIF_OP_SET, ESP_NETIF_DOMAIN_NAME_SERVER, &oferta, sizeof oferta));
    ESP_ERROR_CHECK(esp_netif_set_dns_info(ap_netif, ESP_NETIF_DNS_MAIN, &dns));
    ESP_ERROR_CHECK_WITHOUT_ABORT(esp_netif_dhcps_start(ap_netif));
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, al_evento, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, al_evento, NULL));
    const esp_timer_create_args_t tv = {.callback = al_vencer_validacion, .name = "validacion"};
    const esp_timer_create_args_t tr = {.callback = al_reiniciar, .name = "reinicio"};
    const esp_timer_create_args_t ti = {.callback = al_reintentar, .name = "reintento"};
    ESP_ERROR_CHECK(esp_timer_create(&tv, &s_t_validacion));
    ESP_ERROR_CHECK(esp_timer_create(&tr, &s_t_reinicio));
    ESP_ERROR_CHECK(esp_timer_create(&ti, &s_t_reintento));
    wifi_config_t ap = {
        .ap = {
            .channel = 1,
            .authmode = WIFI_AUTH_OPEN,
            .max_connection = 4,
        },
    };
    size_t n = strlen(s_id);
    memcpy(ap.ap.ssid, s_id, n);
    ap.ap.ssid_len = n;
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(portal_dns_iniciar());
    ESP_ERROR_CHECK(portal_http_iniciar(s_id, s_version, al_enviar));
}

static void ejecutar(con_estado_t origen, con_evento_t ev, con_transicion_t t)
{
    switch (t.accion) {
    case CON_ACC_ARRANCAR_PORTAL:      arrancar_portal(); break;
    case CON_ACC_ARRANCAR_STA:         /* T01: llega con JRN-01.3 */ break;
    case CON_ACC_RESPONDER_ERRORES:    /* T03: la respuesta la da el adaptador del portal */ break;
    case CON_ACC_PROBAR_UNION:         probar_union(); break;
    case CON_ACC_PERSISTIR:            persistir_y_reiniciar(); break;
    case CON_ACC_RESPONDER_NO_CONECTA: no_conecta(); break;
    case CON_ACC_RESPONDER_OCUPADO:    /* T07: la respuesta la da el adaptador del portal */ break;
    case CON_ACC_NINGUNA:              break;
    }
    /* E0 */
    ESP_LOGI(TAG, "con: %s -> %s (%s)", con_nombre_estado(origen),
             con_nombre_estado(t.siguiente), con_nombre_evento(ev));
}

void app_main(void)
{
    const esp_app_desc_t *app = esp_app_get_description();
    uint8_t mac[6];
    ESP_ERROR_CHECK(esp_read_mac(mac, ESP_MAC_WIFI_STA));
    identidad_desde_mac(mac, s_id);
    s_version = app->version;
    log_boot(app->version);                       /* E1: la primera línea de la aplicación */
    ESP_LOGI(TAG, "nodo_clima %s", app->version);
#if CONFIG_NODO_BENCH_BUILD
    ESP_LOGI(TAG, "%s", BENCH_MARKER);
#endif
    s_lock = xSemaphoreCreateRecursiveMutex();

    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    transicion(CON_EV_FIN_ARRANQUE, (con_guardas_t){.config_valida = config_valida()});

    /* Marcador de arranque del contrato del testbench: última línea de app_main. */
    ESP_LOGI(TAG, "Init complete");
}
