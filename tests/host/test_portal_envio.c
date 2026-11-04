/* TC-POR-04 · FR-POR-04 (host): la respuesta a un envío inválido.
 * Decodificación del cuerpo urlencoded y formulario con errores: aviso
 * general, error bajo cada campo inválido (identificado por su name),
 * valores no secretos conservados y secretos nunca rellenos. */
#include <stdio.h>
#include <string.h>
#include "portal_urlenc.h"
#include "portal_validar.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)
#define IGUAL(a, b) ((a) && strcmp((a), (b)) == 0)

int main(void)
{
    /* Decodificación */
    char body[] = "wifi_ssid=Mi+Red%21&wifi_pass=clave%20123&mqtt_host=broker.local&mqtt_port=1883"
                  "&mqtt_user=&sitio=sitio1&zona=Zona%231&desconocido=x&zona=otra&mqtt_pass=a%2Gb";
    const char *v[PORTAL_N_CAMPOS];
    portal_decodificar(body, v);
    ESPERA(IGUAL(v[PORTAL_WIFI_SSID], "Mi Red!"), "wifi_ssid '%s'", v[PORTAL_WIFI_SSID] ? v[PORTAL_WIFI_SSID] : "(null)");
    ESPERA(IGUAL(v[PORTAL_WIFI_PASS], "clave 123"), "wifi_pass");
    ESPERA(IGUAL(v[PORTAL_MQTT_HOST], "broker.local"), "mqtt_host");
    ESPERA(IGUAL(v[PORTAL_MQTT_PORT], "1883"), "mqtt_port");
    ESPERA(IGUAL(v[PORTAL_MQTT_USER], ""), "mqtt_user vacío presente");
    ESPERA(IGUAL(v[PORTAL_SITIO], "sitio1"), "sitio");
    ESPERA(IGUAL(v[PORTAL_ZONA], "Zona#1"), "zona: la primera aparición cuenta");
    ESPERA(IGUAL(v[PORTAL_MQTT_PASS], "a%2Gb"), "%%XX mal formado se conserva literal: '%s'", v[PORTAL_MQTT_PASS] ? v[PORTAL_MQTT_PASS] : "(null)");
    char vacio[] = "";
    portal_decodificar(vacio, v);
    for (int i = 0; i < PORTAL_N_CAMPOS; i++) ESPERA(v[i] == NULL, "cuerpo vacío: campo %d no es NULL", i);

    /* Formulario con errores: zona y wifi_pass inválidos */
    char b2[] = "wifi_ssid=red-de-prueba&wifi_pass=corta&mqtt_host=broker.local&mqtt_port=1883"
                "&sitio=sitio1&zona=Zona%231";
    portal_decodificar(b2, v);
    portal_validacion_t r;
    portal_validar(v, &r);
    ESPERA(r.n_errores == 2 && r.error[PORTAL_ZONA] && r.error[PORTAL_WIFI_PASS], "validación: %d errores", r.n_errores);
    portal_form_t f = {.id = "clima-a1b2c3", .version = "0.3.0"};
    memcpy(f.valores, v, sizeof f.valores);
    memcpy(f.error, r.error, sizeof f.error);
    static char html[8192];
    size_t n = portal_form_html(html, sizeof html, &f);
    ESPERA(n > 0, "no cabe");
    ESPERA(strstr(html, "class=\"aviso\""), "falta el aviso general");
    ESPERA(strstr(html, "id=\"err-zona\"") && strstr(html, "id=\"err-wifi_pass\""), "falta el error de un campo inválido");
    ESPERA(!strstr(html, "id=\"err-wifi_ssid\"") && !strstr(html, "id=\"err-sitio\"") && !strstr(html, "id=\"err-mqtt_host\""),
           "error en un campo válido");
    /* El error va debajo de su campo: después de su <input> y antes del siguiente */
    const char *in_zona = strstr(html, "name=\"zona\""), *err_zona = strstr(html, "id=\"err-zona\"");
    ESPERA(in_zona && err_zona && err_zona > in_zona, "err-zona no está debajo de zona");
    /* Valores no secretos conservados; secretos nunca */
    ESPERA(strstr(html, "value=\"red-de-prueba\"") && strstr(html, "value=\"broker.local\"") && strstr(html, "value=\"sitio1\""),
           "no conserva los valores no secretos");
    ESPERA(strstr(html, "value=\"Zona#1\""), "no conserva el valor inválido de zona");
    ESPERA(!strstr(html, "corta"), "la contraseña inválida vuelve rellena");

    /* Sin errores: sin aviso ni err-* */
    portal_form_t g = {.id = "clima-a1b2c3", .version = "0.3.0"};
    portal_form_html(html, sizeof html, &g);
    ESPERA(!strstr(html, "class=\"aviso\"") && !strstr(html, "id=\"err-"), "aviso o error sin errores");

    printf("TC-POR-04 (FR-POR-04): %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
