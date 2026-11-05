/* TC-POR-01 · FR-POR-03 (host): el generador del formulario.
 * Verifica los atributos name de §17, nunca las etiquetas visibles. */
#include <stdio.h>
#include <string.h>
#include "portal_form.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

static const char *NAMES_17[] = {"wifi_ssid", "wifi_pass", "mqtt_host", "mqtt_port",
                                 "mqtt_user", "mqtt_pass", "zona", "sitio"};

/* Devuelve la etiqueta <input …> que lleva name="n", o NULL. */
static const char *input_de(const char *html, const char *n, char *out, size_t cap)
{
    char pat[64];
    snprintf(pat, sizeof pat, "name=\"%s\"", n);
    const char *p = strstr(html, pat);
    if (!p) return NULL;
    const char *a = p; while (a > html && *a != '<') a--;
    const char *b = strchr(p, '>');
    if (!b || strncmp(a, "<input", 6) != 0) return NULL;
    size_t len = (size_t)(b - a + 1) < cap - 1 ? (size_t)(b - a + 1) : cap - 1;
    memcpy(out, a, len); out[len] = 0;
    return out;
}

static int cuenta(const char *h, const char *s) { int n = 0; for (const char *p = h; (p = strstr(p, s)); p++) n++; return n; }

int main(void)
{
    static char html[8192];
    char tag[512];
    portal_form_t f = {.id = "clima-a1b2c3", .version = "0.3.0"};
    /* Un valor para cada secreto: no debe salir nunca */
    f.valores[PORTAL_WIFI_PASS] = "SECRETO-wifi-123";
    f.valores[PORTAL_MQTT_PASS] = "SECRETO-mqtt-456";
    size_t n = portal_form_html(html, sizeof html, &f);
    ESPERA(n > 0 && n == strlen(html), "longitud %zu", n);

    /* Los 8 campos de §17, cada uno una sola vez, en un <input> */
    for (size_t i = 0; i < sizeof NAMES_17 / sizeof *NAMES_17; i++) {
        char pat[64]; snprintf(pat, sizeof pat, "name=\"%s\"", NAMES_17[i]);
        ESPERA(cuenta(html, pat) == 1, "%s aparece %d veces", NAMES_17[i], cuenta(html, pat));
        ESPERA(input_de(html, NAMES_17[i], tag, sizeof tag), "%s no es un <input>", NAMES_17[i]);
    }
    ESPERA(cuenta(html, "<input ") == 8, "hay %d <input> (esperados 8)", cuenta(html, "<input "));

    /* Secretos: type=password, sin value, y el valor recibido no aparece en ningún sitio */
    const char *secretos[] = {"wifi_pass", "mqtt_pass"};
    for (int i = 0; i < 2; i++) {
        ESPERA(input_de(html, secretos[i], tag, sizeof tag) && strstr(tag, "type=\"password\""), "%s no es password", secretos[i]);
        ESPERA(input_de(html, secretos[i], tag, sizeof tag) && !strstr(tag, "value="), "%s lleva value: %s", secretos[i], tag);
    }
    ESPERA(!strstr(html, "SECRETO-"), "un secreto sale relleno");

    /* H-39: el teclado del teléfono no pone mayúsculas ni corrige en los campos de texto */
    const char *texto[] = {"wifi_ssid", "mqtt_host", "mqtt_user", "sitio", "zona"};
    for (int i = 0; i < 5; i++)
        ESPERA(input_de(html, texto[i], tag, sizeof tag) && strstr(tag, "autocapitalize=\"none\"") &&
               strstr(tag, "autocorrect=\"off\"") && strstr(tag, "spellcheck=\"false\""), "%s sin los atributos de H-39", texto[i]);

    /* Puerto por defecto 1883 (§17) */
    ESPERA(input_de(html, "mqtt_port", tag, sizeof tag) && strstr(tag, "value=\"1883\""), "mqtt_port sin 1883: %s", tag);

    /* Envío al propio portal, por POST */
    ESPERA(strstr(html, "<form") && strstr(html, "method=\"post\"") && strstr(html, "action=\"/\""), "formulario sin POST a /");

    /* Id y versión del firmware visibles */
    ESPERA(strstr(html, "clima-a1b2c3") && strstr(html, "0.3.0"), "sin id o versión");

    /* Sin recursos externos (el teléfono no tiene Internet en el AP del nodo) */
    ESPERA(!strstr(html, "http://") && !strstr(html, "https://") && !strstr(html, "src=") && !strstr(html, "<link"),
           "hay un recurso externo");

    /* Los valores conservados se escapan */
    portal_form_t g = {.id = "clima-a1b2c3", .version = "0.3.0"};
    g.valores[PORTAL_WIFI_SSID] = "a\"><script>x</script>&";
    portal_form_html(html, sizeof html, &g);
    ESPERA(!strstr(html, "<script>x"), "valor sin escapar");
    ESPERA(input_de(html, "wifi_ssid", tag, sizeof tag) && strstr(tag, "value=\"a&quot;&gt;&lt;script&gt;x&lt;/script&gt;&amp;\""), "escape: %s", tag);

    /* Buffer pequeño: 0, nunca un HTML truncado */
    char peq[64];
    ESPERA(portal_form_html(peq, sizeof peq, &f) == 0, "buffer pequeño no devuelve 0");

    printf("TC-POR-01 (FR-POR-03): %s\n", fallos ? "FALLO" : "ok");
    return fallos != 0;
}
