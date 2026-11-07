/* TC-HA-01 · FR-HA-02, FR-HA-03 (host): generador de Discovery (FSD §10.2, §10.4).
 * Contrato: nodo clima-a1b2c3, sitio sitio1, zona zona1, fw 0.3.0 → JSON idéntico
 * campo a campo a §10.2; unique_id sin sitio ni zona; expire_after = 180. */
#include <stdio.h>
#include <string.h>
#include "ha_discovery.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)
#define IGUAL(obt, esp) ESPERA(strcmp((obt), (esp)) == 0, "\n  obtenido: %s\n  esperado: %s", (obt), (esp))

/* §10.2, literal (temperatura) */
static const char *const TEMP_10_2 =
    "{\"name\":\"Temperatura\",\"unique_id\":\"clima-a1b2c3_temperatura\","
    "\"state_topic\":\"sitio1/zona1/clima-a1b2c3/temperatura\","
    "\"value_template\":\"{{ value_json.v }}\",\"unit_of_measurement\":\"°C\","
    "\"device_class\":\"temperature\",\"state_class\":\"measurement\",\"expire_after\":180,"
    "\"availability_topic\":\"sitio1/zona1/clima-a1b2c3/status\","
    "\"availability_template\":\"{{ value_json.estado }}\","
    "\"payload_available\":\"online\",\"payload_not_available\":\"offline\","
    "\"device\":{\"identifiers\":[\"clima-a1b2c3\"],\"name\":\"Clima sitio1 zona1\","
    "\"model\":\"Waveshare ESP32-S3-DEV-KIT-N8R8 + SHT41\",\"sw_version\":\"0.3.0\"}}";

static void ha01(void)
{
    char b[1024], t[128];
    int n = had_config_json(b, sizeof b, "sitio1", "zona1", "clima-a1b2c3", "0.3.0", HAD_TEMPERATURA);
    IGUAL(b, TEMP_10_2);
    ESPERA(n == (int)strlen(b), "longitud %d", n);

    /* humedad: device_class humidity, unidad %; punto_rocio: temperature, °C, «Punto de rocío» */
    had_config_json(b, sizeof b, "sitio1", "zona1", "clima-a1b2c3", "0.3.0", HAD_HUMEDAD);
    ESPERA(strstr(b, "\"name\":\"Humedad\",\"unique_id\":\"clima-a1b2c3_humedad\","
                     "\"state_topic\":\"sitio1/zona1/clima-a1b2c3/humedad\"") != NULL, "%s", b);
    ESPERA(strstr(b, "\"unit_of_measurement\":\"%\",\"device_class\":\"humidity\"") != NULL, "%s", b);
    had_config_json(b, sizeof b, "sitio1", "zona1", "clima-a1b2c3", "0.3.0", HAD_PUNTO_ROCIO);
    ESPERA(strstr(b, "\"name\":\"Punto de rocío\",\"unique_id\":\"clima-a1b2c3_punto_rocio\","
                     "\"state_topic\":\"sitio1/zona1/clima-a1b2c3/punto_rocio\"") != NULL, "%s", b);
    ESPERA(strstr(b, "\"unit_of_measurement\":\"°C\",\"device_class\":\"temperature\"") != NULL, "%s", b);

    /* FR-HA-03: expire_after = 180 en las tres */
    for (int m = 0; m < HAD_N_MEDIDAS; m++) {
        had_config_json(b, sizeof b, "sitio1", "zona1", "clima-a1b2c3", "0.3.0", (had_medida_t)m);
        ESPERA(strstr(b, ",\"expire_after\":180,") != NULL, "medida %d sin expire_after 180", m);
    }

    /* Prohibido: unique_id dependiente de la zona o del sitio; sw_version = la versión dada */
    char otro[1024];
    had_config_json(otro, sizeof otro, "sitio2", "garaje", "clima-a1b2c3", "0.4.1", HAD_TEMPERATURA);
    ESPERA(strstr(otro, "\"unique_id\":\"clima-a1b2c3_temperatura\"") != NULL, "%s", otro);
    ESPERA(strstr(otro, "\"identifiers\":[\"clima-a1b2c3\"]") != NULL, "%s", otro);
    ESPERA(strstr(otro, "\"name\":\"Clima sitio2 garaje\"") != NULL, "%s", otro);
    ESPERA(strstr(otro, "\"sw_version\":\"0.4.1\"}}") != NULL, "%s", otro);

    /* Tópicos */
    had_topico(t, sizeof t, "clima-a1b2c3", HAD_TEMPERATURA);
    IGUAL(t, "homeassistant/sensor/clima-a1b2c3/temperatura/config");
    had_topico(t, sizeof t, "clima-a1b2c3", HAD_HUMEDAD);
    IGUAL(t, "homeassistant/sensor/clima-a1b2c3/humedad/config");
    had_topico(t, sizeof t, "clima-a1b2c3", HAD_PUNTO_ROCIO);
    IGUAL(t, "homeassistant/sensor/clima-a1b2c3/punto_rocio/config");

    /* Escape de la versión; nunca trunca; medida inexistente */
    had_config_json(b, sizeof b, "sitio1", "zona1", "clima-a1b2c3", "0.3.0-\"x\\", HAD_HUMEDAD);
    ESPERA(strstr(b, "\"sw_version\":\"0.3.0-\\\"x\\\\\"}}") != NULL, "%s", b);
    n = had_config_json(b, 100, "sitio1", "zona1", "clima-a1b2c3", "0.3.0", HAD_TEMPERATURA);
    ESPERA(n == -1 && b[0] == '\0', "sin espacio: n=%d", n);
    n = had_topico(t, 20, "clima-a1b2c3", HAD_TEMPERATURA);
    ESPERA(n == -1 && t[0] == '\0', "tópico sin espacio: n=%d", n);
    n = had_config_json(b, sizeof b, "sitio1", "zona1", "clima-a1b2c3", "0.3.0", HAD_N_MEDIDAS);
    ESPERA(n == -1 && b[0] == '\0', "medida inexistente: n=%d", n);
}

int main(void)
{
    ha01();
    if (fallos) { printf("%d fallo(s)\n", fallos); return 1; }
    puts("TC-HA-01: ok");
    return 0;
}
