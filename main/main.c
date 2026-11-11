/*
 * Nodo Clima Piloto — raíz de composición.
 *
 * Crea los adaptadores y conecta los núcleos puros (components/). Implementado
 * hasta ahora: identidad (FR-ID-01), línea boot: (E1), lectura de la
 * configuración (E2) y filas T02–T07 de la tabla: el portal (AP abierto, DNS
 * cautivo, HTTP, validación del envío) y la prueba de unión con su resultado
 * (guardar y reiniciar, o «no se pudo conectar»), y T01 en su parte de
 * arrancar el STA con la configuración guardada (E4). Pendiente, cada uno con su
 * test: el resto de §6.3. T08 arranca el cliente MQTT y SNTP (§13: una petición
 * cada 10 s sin hora válida, resincronización cada hora), T09/T10 reintentan la unión con el backoff de FR-CON-02 y T11–T16
 * llevan el broker (§9): status online al conectar, medidas y status en cada
 * ciclo en OPERATIVO, Last Will offline. El ciclo de medición (FSD §5.4) lee
 * el SHT41 cada 60 s en cualquier estado y escribe E3.
 */
#include <string.h>
#include <sys/time.h>
#include <time.h>
#include "esp_app_desc.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_netif.h"
#include "esp_ota_ops.h"
#include "esp_sntp.h"
#include "esp_system.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "mqtt_client.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "sdkconfig.h"

#include "conectividad.h"
#include "conectividad_backoff.h"
#include "diag_reset.h"
#include "identidad.h"
#include "medicion.h"
#include "sht41.h"
#include "conectividad_sta.h"
#include "ota_diag.h"
#include "portal_config.h"
#include "portal_dns.h"
#include "portal_http.h"
#include "portal_validar.h"
#include "publicador.h"
#include "ha_discovery.h"
#include "hora.h"
#include "udplog.h"

static const char *TAG = "nodo";
static char s_id[IDENTIDAD_LEN];
static const char *s_version;

/* Estado del gestor. Lo cambian el arranque, el servidor HTTP y los eventos
 * Wi-Fi (tareas distintas): toda transición pasa por s_lock. */
static con_estado_t s_estado = CON_ARRANQUE;
static SemaphoreHandle_t s_lock;

static portal_config_t s_pendiente;            /* datos del envío en prueba (T04..T06) */
static portal_config_t s_cfg;                  /* configuración leída de la NVS (T01) */
static int s_intento;                          /* E4: <n> del intento de unión en curso */
static const char *const *s_envio;             /* valores del envío, solo durante al_enviar */
static esp_timer_handle_t s_t_validacion;      /* T06: 20 s sin IP */
static esp_timer_handle_t s_t_portal;          /* T24: 10 min de portal desde T02 (FR-POR-08, D24) */
static bool s_cierre_pendiente;                /* T25: el portal venció durante VALIDANDO */
static esp_timer_handle_t s_t_reinicio;        /* T05: reinicio tras responder */
static esp_timer_handle_t s_t_reintento;       /* T04: reintento de la unión dentro de los 20 s */
static esp_timer_handle_t s_t_backoff;         /* T09/T10: backoff de Wi-Fi (FR-CON-02) */
static con_backoff_t s_backoff_wifi;
static esp_timer_handle_t s_t_backoff_mqtt;    /* T12/T13/T15: backoff MQTT (FR-CON-02) */
static esp_timer_handle_t s_t_primer_mqtt;     /* T08: primer intento MQTT, después de su línea E0 */
static con_backoff_t s_backoff_mqtt;
static esp_mqtt_client_handle_t s_mqtt;        /* creado en el primer T08 */
static bool s_mqtt_activo;                     /* el cliente está arrancado (start sin stop) */
static int s_intento_mqtt;                     /* E5: <n> del intento MQTT en curso */
static QueueHandle_t s_eventos_mqtt;           /* mqtt_up / mqtt_down hacia la tarea del gestor */
static char s_top_status[160];                 /* <sitio>/<zona>/<nodo>/status */

#define VALIDACION_US   (20 * 1000 * 1000)     /* T06, D12: 20 s */
#define PORTAL_US       (600LL * 1000 * 1000)  /* T24, D24: 10 min desde T02 */
#define REINICIO_US     (4 * 1000 * 1000)      /* T05: ≤ 5 s desde la línea con: (D12); 4 s para que el teléfono vea «Conectado…» (H-41) */
#define REINTENTO_US    (1 * 1000 * 1000)

#if CONFIG_NODO_BENCH_BUILD
/* Marcador que la CI busca en el binario (FSD C-LOG-01). Solo existe en la
 * imagen de banco; la de producción no debe contenerlo. */
static const char BENCH_MARKER[] = "NODO-BENCH-IMAGE";
#endif

/* Watchdog de tareas (NFR-WDT-01, D16: 30 s; CONFIG_ESP_TASK_WDT_TIMEOUT_S y _PANIC en
 * sdkconfig.defaults). Las tareas de medición y de conectividad se suscriben y lo
 * alimentan al menos cada WDT_ALIMENTO_MS; si una deja de hacerlo 30 s, el nodo se
 * reinicia con reset = task_wdt desde cualquier estado (acción global de §6.3). */
#define WDT_ALIMENTO_MS 5000
static volatile bool s_wdt_bloquear;          /* E13 wdt-test: la medición deja de alimentarlo */

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
/* Traducción de esp_reset_reason() a la causa de §9.3 (FSD 0.9.4); el nombre lo da
 * diag_reset (núcleo puro, TC-DIAG-01). Lo que no tiene valor propio es «otro». */
static const char *causa_reset(void)
{
    diag_reset_t c;
    switch (esp_reset_reason()) {
    case ESP_RST_POWERON:   c = DIAG_RESET_POWERON; break;
    case ESP_RST_EXT:       c = DIAG_RESET_EXT; break;
    case ESP_RST_SW:        c = DIAG_RESET_SW; break;
    case ESP_RST_PANIC:     c = DIAG_RESET_PANIC; break;
    case ESP_RST_TASK_WDT:  c = DIAG_RESET_TASK_WDT; break;
    case ESP_RST_INT_WDT:   c = DIAG_RESET_INT_WDT; break;
    case ESP_RST_WDT:       c = DIAG_RESET_WDT; break;
    case ESP_RST_DEEPSLEEP: c = DIAG_RESET_DEEPSLEEP; break;
    case ESP_RST_BROWNOUT:  c = DIAG_RESET_BROWNOUT; break;
    case ESP_RST_USB:       c = DIAG_RESET_USB; break;
    case ESP_RST_JTAG:      c = DIAG_RESET_JTAG; break;
    default:                c = DIAG_RESET_OTRO; break;
    }
    return diag_reset_nombre(c);
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
    if (val.n_errores) { memset(&c, 0, sizeof c); return false; }
    ESP_LOGI(TAG, "cfg: sitio=%s zona=%s", c.sitio, c.zona);   /* E2 */
    s_cfg = c;                                                  /* para T01 */
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
    con_transicion_t t = transicion(CON_EV_ENVIO, (con_guardas_t){.envio_valido = valido,
                                                                    .cierre_pendiente = s_cierre_pendiente});
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
        s_intento = 0;
        transicion(CON_EV_WIFI_UP, (con_guardas_t){0});
    }
}

/* E4: cada intento de unión STA escribe «wifi: intento <n>»; <n> vuelve a 1
 * tras cada conexión lograda. */
static void intentar_union(void)
{
    ESP_LOGI(TAG, "wifi: intento %d", ++s_intento);
    esp_wifi_connect();
}

static void al_reintentar(void *arg)
{
    xSemaphoreTakeRecursive(s_lock, portMAX_DELAY);
    if (s_estado == CON_VALIDANDO) intentar_union();
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
static void crear_sta(void)
{
    static bool creado;
    if (!creado) { esp_netif_create_default_wifi_sta(); creado = true; }
}

/* FR-CON-07 (SEC-07): con clave, umbral WPA2-PSK (nunca una red abierta con el mismo
 * SSID) y PMF capaz; sin clave, red abierta. Lo decide el núcleo puro. */
static void configurar_sta(const portal_config_t *c)
{
    wifi_config_t sta = {0};
    memcpy(sta.sta.ssid, c->wifi_ssid, strlen(c->wifi_ssid));
    memcpy(sta.sta.password, c->wifi_pass, strlen(c->wifi_pass));
    const con_sta_seguridad_t seg = con_sta_seguridad(c->wifi_pass);
    sta.sta.threshold.authmode = seg.umbral == CON_STA_UMBRAL_WPA2_PSK ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;
    sta.sta.pmf_cfg.capable = seg.pmf_capaz;
    sta.sta.pmf_cfg.required = seg.pmf_requerido;
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &sta));
    memset(&sta, 0, sizeof sta);
}

static void probar_union(void)
{
    if (portal_config_desde(s_envio, &s_pendiente) != 0) {   /* validado: no debería ocurrir */
        ESP_LOGE(TAG, "portal: envío válido que no cabe en el registro");
        esp_timer_start_once(s_t_validacion, 1);            /* sale por T06 */
        return;
    }
    crear_sta();
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));
    configurar_sta(&s_pendiente);
    esp_timer_start_once(s_t_validacion, VALIDACION_US);
    s_intento = 0;
    intentar_union();
}

static void intentar_mqtt(void);

/* ---- Adaptador SNTP (§13) ---------------------------------------------------
 * El cliente SNTP de lwIP pide la hora; el planificador (components/hora) decide
 * cuándo: con IP, un tick cada 10 s; sin hora válida, una petición por tick
 * (FR-TIME-06); con hora, un intento cada hora (FR-TIME-04). Cada petición
 * reinicia el cliente de lwIP, que la envía al arrancar. El estado del
 * planificador lo tocan el tick (tarea esp_timer) y el aviso de sincronización
 * (tarea de lwIP): va bajo s_mux_hora, y fuera de él se escribe el log y se
 * llama a lwIP (nunca desde el aviso, que corre en la propia tarea de lwIP). */
#define SNTP_SERVIDOR "pool.ntp.org"            /* FR-TIME-01 */
static hora_sntp_t s_hora;
static portMUX_TYPE s_mux_hora = portMUX_INITIALIZER_UNLOCKED;
static esp_timer_handle_t s_t_sntp;
static int64_t s_build_epoch = -1;

static int64_t ahora_ms(void) { return esp_timer_get_time() / 1000; }

/* FR-TIME-02: sincronizada en este arranque y no anterior a la fecha de build */
static bool hora_valida(void)
{
    taskENTER_CRITICAL(&s_mux_hora);
    bool sinc = s_hora.sincronizado;
    taskEXIT_CRITICAL(&s_mux_hora);
    return hora_es_valida(sinc, (int64_t)time(NULL), s_build_epoch);
}

static void al_sincronizar(struct timeval *tv)
{
    taskENTER_CRITICAL(&s_mux_hora);
    hora_sincronizada(&s_hora, ahora_ms());
    taskEXIT_CRITICAL(&s_mux_hora);
    ESP_LOGI(TAG, "sntp: sincronizado ts=%lld", (long long)tv->tv_sec);      /* E6 */
}

static void al_tick_sntp(void *arg)
{
    taskENTER_CRITICAL(&s_mux_hora);
    unsigned acc = hora_tick(&s_hora, ahora_ms());
    taskEXIT_CRITICAL(&s_mux_hora);
    if (acc & HORA_FALLO) ESP_LOGW(TAG, "sntp: fallo");                       /* E6 */
    if (acc & HORA_PEDIR) {
        ESP_LOGI(TAG, "sntp: inicio %s", SNTP_SERVIDOR);                        /* E6 */
        esp_sntp_stop();
        esp_sntp_init();
    } else if (esp_sntp_enabled()) {
        esp_sntp_stop();                        /* sincronizado o intento terminado: sin sondeo propio de lwIP */
    }
    esp_timer_start_once(s_t_sntp, (uint64_t)HORA_TICK_MS * 1000u);
}

static void sntp_configurar(const char *fecha, const char *hora)
{
    s_build_epoch = hora_build_epoch(fecha, hora);
    hora_iniciar(&s_hora);
    esp_sntp_setoperatingmode(ESP_SNTP_OPMODE_POLL);
    esp_sntp_setservername(0, SNTP_SERVIDOR);
    sntp_set_time_sync_notification_cb(al_sincronizar);
    const esp_timer_create_args_t ts = {.callback = al_tick_sntp, .name = "sntp"};
    ESP_ERROR_CHECK(esp_timer_create(&ts, &s_t_sntp));
}

/* Acción de T08: reiniciar el backoff de Wi-Fi (<n> de E4 vuelve a 1 en el
 * siguiente intento), arrancar el cliente MQTT con su primer intento (E5) y
 * SNTP (§13). Sin AP y sin publicar hasta T11 (T08, «No debe ocurrir»). */
static void red_lista(void)
{
    esp_timer_stop(s_t_backoff);
    con_backoff_reiniciar(&s_backoff_wifi);
    s_intento = 0;
    esp_timer_stop(s_t_backoff_mqtt);
    con_backoff_reiniciar(&s_backoff_mqtt);
    s_intento_mqtt = 0;
    esp_timer_start_once(s_t_primer_mqtt, 1000);   /* tras la línea con: de T08 (§6.6), muy dentro de su 1 s */
    esp_timer_stop(s_t_sntp);
    esp_timer_start_once(s_t_sntp, 500 * 1000);     /* primera petición tras la línea con: de T08 (FR-TIME-06) */
}

/* Acción de T09: programar el reintento con el backoff de FR-CON-02. Si ya hay
 * uno armado (un segundo aviso de desconexión del mismo intento), no se cuenta
 * otro fallo: un intento fallido avanza el backoff una sola vez. */
static void programar_reintento(void)
{
    if (esp_timer_is_active(s_t_backoff)) return;
    unsigned ms = con_backoff_fallo(&s_backoff_wifi);
    esp_timer_start_once(s_t_backoff, (uint64_t)ms * 1000u);
}

static void al_vencer_backoff(void *arg)
{
    transicion(CON_EV_BACKOFF, (con_guardas_t){0});      /* T10 */
}

/* ---- Adaptador MQTT (§9) ---------------------------------------------------
 * El cliente esp-mqtt corre sin reconexión automática: cada intento lo lanza
 * la tabla (T08, T13) y los fallos siguen el backoff MQTT de FR-CON-02 (T12,
 * T15). Sus eventos no tocan el gestor desde la tarea del cliente: van por una
 * cola a la tarea «gestor», que nunca espera al cliente con s_lock tomado
 * mientras el cliente la espera a ella. */

static uint32_t s_lecturas, s_err_sensor;
static med_lectura_t s_ultima;                  /* la medida más reciente (T11) */
static bool s_hay_medida;
static bool s_ultima_ts_valido;                 /* ts de s_ultima (FR-TIME-03) */
static int64_t s_ultima_ts;

static void al_evento_mqtt(void *arg, esp_event_base_t base, int32_t id, void *datos)
{
    con_evento_t ev;
    if (id == MQTT_EVENT_CONNECTED) ev = CON_EV_MQTT_UP;
    else if (id == MQTT_EVENT_DISCONNECTED) ev = CON_EV_MQTT_DOWN;
    else return;
    xQueueSend(s_eventos_mqtt, &ev, 0);
}

static void tarea_gestor(void *arg)
{
    con_evento_t ev;
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));                 /* NFR-WDT-01: tarea de conectividad */
    for (;;) {
        esp_task_wdt_reset();
        if (xQueueReceive(s_eventos_mqtt, &ev, pdMS_TO_TICKS(WDT_ALIMENTO_MS)) == pdTRUE)
            transicion(ev, (con_guardas_t){0});
    }
}

static void crear_mqtt(void)
{
    if (s_mqtt) return;
    pub_topico(s_top_status, sizeof s_top_status, s_cfg.sitio, s_cfg.zona, s_id, "status");
    esp_mqtt_client_config_t c = {
        .broker.address = {.hostname = s_cfg.mqtt_host, .port = s_cfg.mqtt_port,
                           .transport = MQTT_TRANSPORT_OVER_TCP},
        .credentials = {.client_id = s_id},
        .session = {.keepalive = 60, .protocol_ver = MQTT_PROTOCOL_V_3_1_1,
                    .last_will = {.topic = s_top_status, .msg = PUB_LWT_OFFLINE, .qos = 1, .retain = 1}},
        .network = {.disable_auto_reconnect = true},
    };
    if (s_cfg.mqtt_user[0]) {                   /* FR-MQTT-07: sin usuario, sin credenciales */
        c.credentials.username = s_cfg.mqtt_user;
        c.credentials.authentication.password = s_cfg.mqtt_pass;
    }
    s_mqtt = esp_mqtt_client_init(&c);
    ESP_ERROR_CHECK(s_mqtt ? ESP_OK : ESP_FAIL);
    ESP_ERROR_CHECK(esp_mqtt_client_register_event(s_mqtt, ESP_EVENT_ANY_ID, al_evento_mqtt, NULL));
}

/* Acción de T13 (y primer intento de T08): E5 y un intento de conexión. */
static void intentar_mqtt(void)
{
    crear_mqtt();
    ESP_LOGI(TAG, "mqtt: intento %d", ++s_intento_mqtt);
    if (!s_mqtt_activo) { s_mqtt_activo = esp_mqtt_client_start(s_mqtt) == ESP_OK; }
    else esp_mqtt_client_reconnect(s_mqtt);
}

/* Acción de T12/T15: un intento fallido avanza el backoff una sola vez. */
static void programar_reintento_mqtt(void)
{
    if (esp_timer_is_active(s_t_backoff_mqtt)) return;
    unsigned ms = con_backoff_fallo(&s_backoff_mqtt);
    esp_timer_start_once(s_t_backoff_mqtt, (uint64_t)ms * 1000u);
}

/* Acción de T14/T16: detener los intentos MQTT y programar un reintento Wi-Fi. */
static void red_caida(void)
{
    esp_timer_stop(s_t_backoff_mqtt);
    esp_timer_stop(s_t_primer_mqtt);
    if (s_mqtt_activo) { esp_mqtt_client_stop(s_mqtt); s_mqtt_activo = false; }
    esp_timer_stop(s_t_sntp);                       /* sin IP no hay peticiones SNTP (FR-TIME-06) */
    esp_sntp_stop();
    programar_reintento();
}

static ota_diag_t s_ota;        /* campo `ota` de status (§9.3, FR-MQTT-09); bajo s_lock */

static void publicar_status(void)
{
    wifi_ap_record_t ap = {0};
    int rssi = esp_wifi_sta_get_ap_info(&ap) == ESP_OK ? ap.rssi : 0;
    char ota[OTA_DIAG_MAX];
    xSemaphoreTakeRecursive(s_lock, portMAX_DELAY);
    memcpy(ota, s_ota.valor, sizeof ota);
    xSemaphoreGiveRecursive(s_lock);
    pub_status_t st = {.online = true, .fw = s_version, .rssi = rssi, .reset = causa_reset(),
                       .uptime_s = (uint32_t)(esp_timer_get_time() / 1000000), .lecturas = s_lecturas,
                       .err_sensor = s_err_sensor, .ota = ota, .hora_valida = hora_valida()};   /* FR-TIME-02 */
    char json[256];
    if (pub_status_json(json, sizeof json, &st) > 0)
        esp_mqtt_client_publish(s_mqtt, s_top_status, json, 0, 1, 1);          /* §9.2: QoS 1, retain */
}

/* FR-MQTT-09: cambio del campo `ota`. E7 «ota: estado <valor>» en cada cambio; con MQTT
 * conectado (OPERATIVO u OTA_DESCARGA) se publica status enseguida (≤ 2 s); sin conexión
 * va en el primer status de T11 (mqtt_listo lo publica siempre). La llamará el adaptador
 * OTA (bloque 5 de la Fase 3); hasta entonces el campo se queda en «ninguno». */
__attribute__((unused)) static void ota_estado(const char *valor)
{
    xSemaphoreTakeRecursive(s_lock, portMAX_DELAY);
    const bool conectado = s_estado == CON_OPERATIVO || s_estado == CON_OTA_DESCARGA;
    const ota_diag_resultado_t r = ota_diag_cambiar(&s_ota, valor, conectado);
    xSemaphoreGiveRecursive(s_lock);
    if (r == OTA_DIAG_INVALIDO) { ESP_LOGE(TAG, "ota: valor de estado no válido"); return; }
    if (r == OTA_DIAG_SIN_CAMBIO) return;
    ESP_LOGI(TAG, "ota: estado %s", valor);                   /* E7 */
    if (r == OTA_DIAG_PUBLICAR_YA) publicar_status();
}

/* Medidas de una lectura válida: QoS 0, retain (FR-MQTT-04); sin punto_rocio si no hay (FR-MED-04).
 * ts = instante de la lectura si la hora era válida; si no, null (FR-TIME-03). */
static void publicar_medidas(const med_lectura_t *m, bool ts_valido, int64_t ts)
{
    const float v[PUB_N_MEDIDAS] = {m->t, m->hr, m->td};
    for (int i = 0; i < PUB_N_MEDIDAS; i++) {
        if (i == PUB_PUNTO_ROCIO && !m->td_valida) continue;
        char top[160], json[64];
        if (pub_topico(top, sizeof top, s_cfg.sitio, s_cfg.zona, s_id, pub_nombre_medida(i)) < 0) continue;
        if (pub_medida_json(json, sizeof json, i, v[i], ts_valido, ts) < 0) continue;
        esp_mqtt_client_publish(s_mqtt, top, json, 0, 0, 1);
    }
}

/* Discovery de Home Assistant (§10.2, FR-HA-01): las tres configuraciones, retain y QoS 1 */
static void publicar_discovery(void)
{
    for (int i = 0; i < HAD_N_MEDIDAS; i++) {
        char top[96], json[768];
        if (had_topico(top, sizeof top, s_id, i) < 0) continue;
        if (had_config_json(json, sizeof json, s_cfg.sitio, s_cfg.zona, s_id, s_version, i) < 0) continue;
        esp_mqtt_client_publish(s_mqtt, top, json, 0, 1, 1);
    }
}

/* Acción de T11: status online, luego Discovery (FR-HA-01), luego las medidas
 * más recientes; reiniciar el backoff MQTT; validar la imagen si está
 * PENDIENTE. No debe: publicar medidas antes que status. */
static void mqtt_listo(void)
{
    esp_timer_stop(s_t_backoff_mqtt);
    con_backoff_reiniciar(&s_backoff_mqtt);
    s_intento_mqtt = 0;
    publicar_status();
    publicar_discovery();
    if (s_hay_medida && s_ultima.valida) publicar_medidas(&s_ultima, s_ultima_ts_valido, s_ultima_ts);
    esp_ota_img_states_t st;
    if (esp_ota_get_state_partition(esp_ota_get_running_partition(), &st) == ESP_OK && st == ESP_OTA_IMG_PENDING_VERIFY)
        esp_ota_mark_app_valid_cancel_rollback();
}

static void al_primer_mqtt(void *arg)
{
    xSemaphoreTakeRecursive(s_lock, portMAX_DELAY);
    if (s_estado == CON_CONECTANDO_BROKER && !s_mqtt_activo) intentar_mqtt();
    xSemaphoreGiveRecursive(s_lock);
}

static void al_vencer_backoff_mqtt(void *arg)
{
    transicion(CON_EV_BACKOFF, (con_guardas_t){0});      /* T13 */
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
        if (s_cierre_pendiente) esp_timer_start_once(s_t_portal, 1000);   /* T25 → T24 */
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
    /* T25: si el portal venció durante la prueba, el evento se vuelve a emitir ya en
     * PORTAL (lo dispara el temporizador, después de la línea con: de T06) y da T24 */
    if (s_cierre_pendiente) esp_timer_start_once(s_t_portal, 1000);
}

static void al_vencer_portal(void *arg)
{
    transicion(CON_EV_PORTAL_VENCE, (con_guardas_t){0});   /* T24 o T25 */
}

/* Acción de T24: apagar el AP y, después, detener el HTTP y el DNS del portal (FSD 0.9.9).
 * La medición sigue; solo un reinicio vuelve a abrir el portal (FR-POR-08). No debe: tocar
 * la NVS. httpd_stop espera a que termine el manejador en curso (un POST, ≤ 20 s por
 * FR-POR-09), y un envío espera a s_lock: la parada corre en una tarea propia, sin s_lock
 * y sin bloquear la tarea esp_timer (N-02, H-85). El AP se apaga primero, así que nadie
 * nuevo llega al portal mientras tanto; el estado ya es ESPERA y un envío no encuentra
 * fila (§6.4, imp¹). */
static void tarea_cierre(void *arg)
{
    esp_wifi_stop();
    portal_http_detener();
    portal_dns_detener();
    vTaskDelete(NULL);
}

static void cerrar_portal(void)
{
    s_cierre_pendiente = false;
    if (xTaskCreate(tarea_cierre, "cierre", 4096, NULL, 5, NULL) != pdPASS) {
        ESP_LOGE(TAG, "portal: sin memoria para cerrar; se apaga el AP");
        esp_wifi_stop();
    }
}

/* Opción DNS del servidor DHCP del AP (OFFER_DNS de lwip dhcpserver.h; el
 * ejemplo wifi/softap_sta de ESP-IDF la define igual). */
#define DHCPS_OFFER_DNS 0x02

/* Acción de T02 (parte implementada): AP Wi-Fi abierto con SSID = id (FR-POR-01),
 * DNS cautivo anunciado por DHCP (FR-POR-02) y servidor HTTP (FR-POR-02..06). */
/* Pila Wi-Fi, eventos y temporizadores, comunes a T01 y T02 (una vez por arranque). */
static void wifi_base(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_ERROR_CHECK(udplog_iniciar());   /* FR-LOG-02 en la imagen de banco; nada en producción */
}

static void wifi_iniciar(void)
{
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, WIFI_EVENT_STA_DISCONNECTED, al_evento, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, al_evento, NULL));
    const esp_timer_create_args_t tv = {.callback = al_vencer_validacion, .name = "validacion"};
    const esp_timer_create_args_t tr = {.callback = al_reiniciar, .name = "reinicio"};
    const esp_timer_create_args_t ti = {.callback = al_reintentar, .name = "reintento"};
    const esp_timer_create_args_t tb = {.callback = al_vencer_backoff, .name = "backoff"};
    ESP_ERROR_CHECK(esp_timer_create(&tb, &s_t_backoff));
    const esp_timer_create_args_t tm = {.callback = al_vencer_backoff_mqtt, .name = "backoff_mqtt"};
    ESP_ERROR_CHECK(esp_timer_create(&tm, &s_t_backoff_mqtt));
    const esp_timer_create_args_t tp = {.callback = al_primer_mqtt, .name = "primer_mqtt"};
    ESP_ERROR_CHECK(esp_timer_create(&tp, &s_t_primer_mqtt));
    ESP_ERROR_CHECK(esp_timer_create(&tv, &s_t_validacion));
    ESP_ERROR_CHECK(esp_timer_create(&tr, &s_t_reinicio));
    ESP_ERROR_CHECK(esp_timer_create(&ti, &s_t_reintento));
}

/* Acción de T01 (parte implementada): arrancar el STA con la configuración
 * guardada y lanzar el primer intento (E4). Sin AP (T01, «No debe ocurrir»). */
static void arrancar_sta(void)
{
    wifi_base();
    crear_sta();
    wifi_iniciar();
    const esp_app_desc_t *app = esp_app_get_description();
    sntp_configurar(app->date, app->time);          /* §13: tras la pila Wi-Fi; arranca en T08 */
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    configurar_sta(&s_cfg);
    ESP_ERROR_CHECK(esp_wifi_start());
    s_intento = 0;
    intentar_union();
}

static void arrancar_portal(void)
{
    wifi_base();
    esp_netif_t *ap_netif = esp_netif_create_default_wifi_ap();
    /* FR-POR-02: el DHCP del AP anuncia 192.168.4.1 como DNS, para que el
     * teléfono pregunte al nodo y su detección de portal llegue aquí */
    esp_netif_dns_info_t dns = {.ip = {.type = ESP_IPADDR_TYPE_V4, .u_addr.ip4.addr = ESP_IP4TOADDR(192, 168, 4, 1)}};
    uint8_t oferta = DHCPS_OFFER_DNS;
    ESP_ERROR_CHECK_WITHOUT_ABORT(esp_netif_dhcps_stop(ap_netif));
    ESP_ERROR_CHECK(esp_netif_dhcps_option(ap_netif, ESP_NETIF_OP_SET, ESP_NETIF_DOMAIN_NAME_SERVER, &oferta, sizeof oferta));
    ESP_ERROR_CHECK(esp_netif_set_dns_info(ap_netif, ESP_NETIF_DNS_MAIN, &dns));
    ESP_ERROR_CHECK_WITHOUT_ABORT(esp_netif_dhcps_start(ap_netif));
    wifi_iniciar();
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
    char ifname[8] = "";
    esp_netif_get_netif_impl_name(ap_netif, ifname);   /* FR-POR-10: el DNS se liga a esta interfaz */
    /* N-03: sin DNS el portal sigue (el formulario se alcanza por 192.168.4.1); E14 lo dice */
    ESP_ERROR_CHECK_WITHOUT_ABORT(portal_dns_iniciar(ifname));
    ESP_ERROR_CHECK(portal_http_iniciar(s_id, s_version, al_enviar));
    const esp_timer_create_args_t tpo = {.callback = al_vencer_portal, .name = "portal"};
    ESP_ERROR_CHECK(esp_timer_create(&tpo, &s_t_portal));
    ESP_ERROR_CHECK(esp_timer_start_once(s_t_portal, PORTAL_US));   /* FR-POR-08 */
}

static void ejecutar(con_estado_t origen, con_evento_t ev, con_transicion_t t)
{
    switch (t.accion) {
    case CON_ACC_ARRANCAR_PORTAL:      arrancar_portal(); break;
    case CON_ACC_ARRANCAR_STA:         arrancar_sta(); break;
    case CON_ACC_RESPONDER_ERRORES:    /* T03: la respuesta la da el adaptador del portal */ break;
    case CON_ACC_PROBAR_UNION:         probar_union(); break;
    case CON_ACC_PERSISTIR:            persistir_y_reiniciar(); break;
    case CON_ACC_RESPONDER_NO_CONECTA: no_conecta(); break;
    case CON_ACC_RESPONDER_OCUPADO:    /* T07: la respuesta la da el adaptador del portal */ break;
    case CON_ACC_RED_LISTA:            red_lista(); break;
    case CON_ACC_PROGRAMAR_REINTENTO:  programar_reintento(); break;
    case CON_ACC_INTENTAR_UNION:       intentar_union(); break;
    case CON_ACC_MQTT_LISTO:           mqtt_listo(); break;
    case CON_ACC_PROGRAMAR_REINTENTO_MQTT: programar_reintento_mqtt(); break;
    case CON_ACC_INTENTAR_MQTT:        intentar_mqtt(); break;
    case CON_ACC_RED_CAIDA:            red_caida(); break;
    case CON_ACC_CERRAR_PORTAL:        cerrar_portal(); break;
    case CON_ACC_APLAZAR_CIERRE:       s_cierre_pendiente = true; break;   /* T25 */
    /* T17–T23 (Fase 3): las filas ya están en el núcleo, pero hoy ningún evento cmd_ota,
     * ota_ok, ota_err ni validacion_vence llega aquí. Sus acciones las implementa el
     * adaptador OTA (bloque 5 del plan de la Fase 3), con la suscripción a cmd/ota. */
    case CON_ACC_INICIAR_DESCARGA:
    case CON_ACC_RECHAZAR_OTA:
    case CON_ACC_REINICIAR_NUEVA:
    case CON_ACC_OTA_FALLIDA:
    case CON_ACC_RECHAZAR_OCUPADO:
    case CON_ACC_ABORTAR_WIFI:
    case CON_ACC_ABORTAR_MQTT:
    case CON_ACC_ROLLBACK:             break;
    case CON_ACC_NINGUNA:              break;
    }
    /* E0 */
    ESP_LOGI(TAG, "con: %s -> %s (%s)", con_nombre_estado(origen),
             con_nombre_estado(t.siguiente), con_nombre_evento(ev));
}

/* Ciclo de medición (FSD §5.4; FR-MED-01/02): cada 60 s con el reloj
 * monotónico del planificador, en cualquier estado. Los contadores son los de
 * `status` (§9.3, Fase 2). */
#define PERIODO_MEDIDA_MS 60000

static void tarea_medicion(void *arg)
{
    (void)arg;
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));                 /* NFR-WDT-01: tarea de medición */
    esp_err_t e = sht41_iniciar();
    if (e != ESP_OK) ESP_LOGE(TAG, "sht41: bus no iniciado (%s)", esp_err_to_name(e));
    TickType_t ultimo = xTaskGetTickCount();
    for (;;) {
        float t = 0, hr = 0;
        sht41_resultado_t r = sht41_leer(&t, &hr);
        med_lectura_t m = med_procesar(r == SHT41_OK, t, hr);
        const bool ts_valido = hora_valida();                 /* FR-TIME-03/05: sin hora, ts = null; nunca se espera */
        const int64_t ts = (int64_t)time(NULL);
        if (m.valida) s_lecturas++; else s_err_sensor++;      /* FR-SEN-02 */
        char linea[MED_LINEA_MAX];
        med_linea(linea, sizeof linea, &m, sht41_motivo(r));
        if (m.valida) ESP_LOGI(TAG, "%s", linea);             /* E3 */
        else          ESP_LOGW(TAG, "%s", linea);
        /* FR-MQTT-08: en OPERATIVO, medidas y status en cada ciclo. Se mira el
         * estado con s_lock y se publica sin él (el cliente puede estar
         * esperando a la tarea del gestor). */
        xSemaphoreTakeRecursive(s_lock, portMAX_DELAY);
        s_ultima = m; s_hay_medida = true;
        s_ultima_ts_valido = ts_valido; s_ultima_ts = ts;
        bool operativo = s_estado == CON_OPERATIVO;
        xSemaphoreGiveRecursive(s_lock);
        if (operativo) {
            if (m.valida) publicar_medidas(&m, ts_valido, ts);
            publicar_status();
        }
        /* Espera al ciclo siguiente en tramos, alimentando el watchdog (NFR-WDT-01); el
         * instante de cada ciclo sigue siendo el del reloj del planificador (FR-MED-01). */
        const TickType_t siguiente = ultimo + pdMS_TO_TICKS(PERIODO_MEDIDA_MS);
        while ((TickType_t)(siguiente - xTaskGetTickCount()) - 1u < pdMS_TO_TICKS(PERIODO_MEDIDA_MS)) {
            if (!s_wdt_bloquear) esp_task_wdt_reset();
            TickType_t falta = siguiente - xTaskGetTickCount();
            vTaskDelay(falta < pdMS_TO_TICKS(WDT_ALIMENTO_MS) ? falta : pdMS_TO_TICKS(WDT_ALIMENTO_MS));
        }
        ultimo = siguiente;
        while (s_wdt_bloquear) vTaskDelay(pdMS_TO_TICKS(1000));   /* E13 wdt-test: sin alimentar */
    }
}

#if CONFIG_NODO_BENCH_BUILD
/* ---- Comandos serie de la imagen de banco (E13, §18; C-LOG-02) ---------------
 * Solo existe con CONFIG_NODO_BENCH_BUILD=y: la imagen de producción no lee la
 * consola. Lee líneas de la consola primaria (UART0) con el driver de la UART
 * instalado solo para recibir (sin búfer de transmisión: el log sigue saliendo
 * por la consola como siempre). */
#include "driver/uart.h"
#define CMD_UART CONFIG_ESP_CONSOLE_UART_NUM
#define CMD_MAX  32

static void tarea_comandos(void *arg)
{
    (void)arg;
    char linea[CMD_MAX];
    size_t n = 0;
    for (;;) {
        uint8_t c;
        if (uart_read_bytes(CMD_UART, &c, 1, portMAX_DELAY) != 1) continue;
        if (c == '\r') continue;
        if (c != '\n') { if (n < sizeof linea - 1) linea[n++] = (char)c; continue; }
        linea[n] = '\0';
        n = 0;
        if (strcmp(linea, "wdt-test") == 0) {
            ESP_LOGW(TAG, "wdt: bloqueando medicion");         /* E13 → NFR-WDT-01 */
            s_wdt_bloquear = true;
        } else if (strcmp(linea, "reiniciar") == 0) {
            esp_restart();                                     /* E13: la siguiente boot: con reset=sw */
        }
    }
}

static void comandos_iniciar(void)
{
    if (uart_driver_install(CMD_UART, 256, 0, 0, NULL, 0) == ESP_OK)
        xTaskCreate(tarea_comandos, "comandos", 3072, NULL, 3, NULL);
    else
        ESP_LOGE(TAG, "comandos: uart %d sin driver", CMD_UART);
}
#endif

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
    ota_diag_iniciar(&s_ota);                     /* §9.3: «ninguno» al arrancar */
    s_eventos_mqtt = xQueueCreate(8, sizeof(con_evento_t));
    xTaskCreate(tarea_gestor, "gestor", 6144, NULL, 6, NULL);   /* T11 serializa Discovery (§10.2) en su pila */

    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    /* FR-MED-02: el ciclo corre en todos los estados, desde el arranque */
    xTaskCreate(tarea_medicion, "medicion", 4096, NULL, 5, NULL);

    transicion(CON_EV_FIN_ARRANQUE, (con_guardas_t){.config_valida = config_valida()});
#if CONFIG_NODO_BENCH_BUILD
    comandos_iniciar();                           /* E13: solo en la imagen de banco (C-LOG-02) */
#endif

    /* Marcador de arranque del contrato del testbench: última línea de app_main. */
    ESP_LOGI(TAG, "Init complete");
}
