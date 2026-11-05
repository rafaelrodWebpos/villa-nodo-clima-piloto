/*
 * Nodo Clima Piloto — raíz de composición.
 *
 * Crea los adaptadores y conecta los núcleos puros (components/). Implementado
 * hasta ahora: identidad (FR-ID-01), línea boot: (E1), guarda de configuración
 * y filas T02 y T03 de la tabla (AP abierto, DNS cautivo y HTTP del portal:
 * GET /, redirecciones y validación del envío, FR-POR-01/02/03/04). Pendiente,
 * cada uno con su test: T04 (prueba de unión), ciclo de medición (FR-MED-*),
 * T01 y el resto de filas de §6.3.
 */
#include <string.h>
#include "esp_app_desc.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_ota_ops.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "sdkconfig.h"

#include "conectividad.h"
#include "identidad.h"
#include "portal_dns.h"
#include "portal_http.h"

static const char *TAG = "nodo";
static char s_id[IDENTIDAD_LEN];
static const char *s_version;
static con_estado_t s_estado = CON_ARRANQUE;

static void ejecutar(con_estado_t origen, con_evento_t ev, con_transicion_t t);

#if CONFIG_NODO_BENCH_BUILD
/* Marcador que la CI busca en el binario (FSD C-LOG-01). Solo existe en la
 * imagen de banco; la de producción no debe contenerlo. */
static const char BENCH_MARKER[] = "NODO-BENCH-IMAGE";
#endif

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

/* Guarda de T01/T02. La configuración (§17) se guarda como un blob en el
 * espacio «nodo»; hasta que exista su escritor (T05, E10) nunca hay una. */
static bool config_valida(void)
{
    nvs_handle_t h;
    if (nvs_open("nodo", NVS_READONLY, &h) != ESP_OK) return false;
    size_t len = 0;
    bool hay = nvs_get_blob(h, "cfg", NULL, &len) == ESP_OK && len > 0;
    nvs_close(h);
    return hay;
}

/* Evento «envío» del portal (hilo del servidor HTTP): T03 si es inválido. */
static void al_enviar(bool valido)
{
    con_estado_t origen = s_estado;
    con_transicion_t t = con_transicion(origen, CON_EV_ENVIO, (con_guardas_t){.envio_valido = valido});
    if (t.fila) {
        s_estado = t.siguiente;
        ejecutar(origen, CON_EV_ENVIO, t);
    }
}

/* Opción DNS del servidor DHCP del AP (OFFER_DNS de lwip dhcpserver.h; el
 * ejemplo wifi/softap_sta de ESP-IDF la define igual). */
#define DHCPS_OFFER_DNS 0x02

/* Acción de T02 (parte implementada): AP Wi-Fi abierto con SSID = id (FR-POR-01),
 * DNS cautivo anunciado por DHCP (FR-POR-02) y servidor HTTP (FR-POR-02/03/04). */
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
    case CON_ACC_ARRANCAR_PORTAL: arrancar_portal(); break;
    case CON_ACC_ARRANCAR_STA:    /* T01: llega con JRN-01.3 */ break;
    case CON_ACC_RESPONDER_ERRORES: /* T03: la respuesta la da el adaptador del portal */ break;
    case CON_ACC_PROBAR_UNION:    /* T04: llega en el commit siguiente */ break;
    case CON_ACC_PERSISTIR:       /* T05: llega en el commit siguiente */ break;
    case CON_ACC_RESPONDER_NO_CONECTA: /* T06: idem */ break;
    case CON_ACC_RESPONDER_OCUPADO: /* T07: idem */ break;
    case CON_ACC_NINGUNA:         break;
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

    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    con_estado_t origen = s_estado;
    con_transicion_t t = con_transicion(origen, CON_EV_FIN_ARRANQUE,
                                        (con_guardas_t){.config_valida = config_valida()});
    s_estado = t.siguiente;   /* antes de la acción: el portal ya puede recibir envíos */
    ejecutar(origen, CON_EV_FIN_ARRANQUE, t);

    /* Marcador de arranque del contrato del testbench: última línea de app_main. */
    ESP_LOGI(TAG, "Init complete");
}
