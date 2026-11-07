/* TC-MQTT-01 · FR-MQTT-02 y TC-MQTT-02 · FR-MQTT-08 (host): serializadores del
 * publicador (FSD §9.2, §9.3, §9.5). «mqtt01»: payload de medida y tópicos;
 * «mqtt02»: `status` con los 9 campos, sus tipos y su orden. */
#include <stdio.h>
#include <string.h>
#include "publicador.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)
#define IGUAL(obt, esp) ESPERA(strcmp((obt), (esp)) == 0, "\n  obtenido: %s\n  esperado: %s", (obt), (esp))

static void mqtt01(void)
{
    char b[128];
    int n;
    /* Contrato de §9.5: T = 21,4 y ts = 1791720000; con ts ausente, null */
    n = pub_medida_json(b, sizeof b, PUB_TEMPERATURA, 21.4f, true, 1791720000);
    IGUAL(b, "{\"v\":21.4,\"u\":\"°C\",\"ts\":1791720000}");
    ESPERA(n == (int)strlen(b), "longitud %d", n);
    pub_medida_json(b, sizeof b, PUB_TEMPERATURA, 21.4f, false, 0);
    IGUAL(b, "{\"v\":21.4,\"u\":\"°C\",\"ts\":null}");
    /* Las otras dos medidas con su unidad; negativos y cero sin «-0.0»; v nunca como string */
    pub_medida_json(b, sizeof b, PUB_HUMEDAD, 48.2f, false, 0);
    IGUAL(b, "{\"v\":48.2,\"u\":\"%\",\"ts\":null}");
    pub_medida_json(b, sizeof b, PUB_PUNTO_ROCIO, -3.5f, true, 1791720060);
    IGUAL(b, "{\"v\":-3.5,\"u\":\"°C\",\"ts\":1791720060}");
    pub_medida_json(b, sizeof b, PUB_PUNTO_ROCIO, -0.0f, false, 0);
    IGUAL(b, "{\"v\":0.0,\"u\":\"°C\",\"ts\":null}");
    pub_medida_json(b, sizeof b, PUB_HUMEDAD, 100.0f, false, 0);
    IGUAL(b, "{\"v\":100.0,\"u\":\"%\",\"ts\":null}");
    /* No cabe: -1 y búfer vacío */
    n = pub_medida_json(b, 10, PUB_TEMPERATURA, 21.4f, true, 1791720000);
    ESPERA(n == -1 && b[0] == '\0', "sin espacio: n=%d b=«%s»", n, b);

    /* Nombres de medida y tópicos de §9.2 (FR-MQTT-01: solo de sitio, zona y nodo) */
    IGUAL(pub_nombre_medida(PUB_TEMPERATURA), "temperatura");
    IGUAL(pub_nombre_medida(PUB_HUMEDAD), "humedad");
    IGUAL(pub_nombre_medida(PUB_PUNTO_ROCIO), "punto_rocio");
    pub_topico(b, sizeof b, "sitio1", "zona1", "clima-a1b2c3", "temperatura");
    IGUAL(b, "sitio1/zona1/clima-a1b2c3/temperatura");
    pub_topico(b, sizeof b, "sitio1", "zona1", "clima-a1b2c3", "status");
    IGUAL(b, "sitio1/zona1/clima-a1b2c3/status");
    n = pub_topico(b, 12, "sitio1", "zona1", "clima-a1b2c3", "status");
    ESPERA(n == -1 && b[0] == '\0', "tópico sin espacio: n=%d", n);
    IGUAL(PUB_LWT_OFFLINE, "{\"estado\":\"offline\"}");
}

static void mqtt02(void)
{
    char b[256];
    /* Ejemplo de §9.3 */
    pub_status_t s = {.online = true, .fw = "0.3.0", .rssi = -61, .reset = "poweron", .uptime_s = 3600,
                      .lecturas = 60, .err_sensor = 0, .ota = "ninguno", .hora_valida = true};
    int n = pub_status_json(b, sizeof b, &s);
    IGUAL(b, "{\"estado\":\"online\",\"fw\":\"0.3.0\",\"rssi\":-61,\"reset\":\"poweron\","
             "\"uptime_s\":3600,\"lecturas\":60,\"err_sensor\":0,\"ota\":\"ninguno\",\"hora_valida\":true}");
    ESPERA(n == (int)strlen(b), "longitud %d", n);
    /* Valores límite y booleano falso; una versión con comillas se escapa (JSON válido) */
    s = (pub_status_t){.online = true, .fw = "0.0.0-9f8d3f8\"x", .rssi = -100, .reset = "usb",
                       .uptime_s = 4294967295u, .lecturas = 0, .err_sensor = 7, .ota = "rechazado:host",
                       .hora_valida = false};
    pub_status_json(b, sizeof b, &s);
    IGUAL(b, "{\"estado\":\"online\",\"fw\":\"0.0.0-9f8d3f8\\\"x\",\"rssi\":-100,\"reset\":\"usb\","
             "\"uptime_s\":4294967295,\"lecturas\":0,\"err_sensor\":7,\"ota\":\"rechazado:host\",\"hora_valida\":false}");
    /* Salida ordenada: offline */
    s.online = false;
    pub_status_json(b, sizeof b, &s);
    ESPERA(strncmp(b, "{\"estado\":\"offline\",", 20) == 0, "offline: %s", b);
    /* Campos nulos: nunca «(null)» ni campos ausentes */
    s = (pub_status_t){.online = true};
    pub_status_json(b, sizeof b, &s);
    IGUAL(b, "{\"estado\":\"online\",\"fw\":\"\",\"rssi\":0,\"reset\":\"otro\","
             "\"uptime_s\":0,\"lecturas\":0,\"err_sensor\":0,\"ota\":\"ninguno\",\"hora_valida\":false}");
    /* No cabe */
    n = pub_status_json(b, 40, &s);
    ESPERA(n == -1 && b[0] == '\0', "sin espacio: n=%d", n);
}

int main(int argc, char **argv)
{
    const char *caso = argc > 1 ? argv[1] : "";
    if (!strcmp(caso, "mqtt01") || !*caso) mqtt01();
    if (!strcmp(caso, "mqtt02") || !*caso) mqtt02();
    printf("%s: %s\n", *caso ? caso : "publicador", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
