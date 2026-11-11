/* TC-OTA-01 · FR-OTA-09, TC-OTA-02 · FR-OTA-14/02/11/13, TC-OTA-03 · FR-OTA-05 (versión),
 * TC-OTA-04 · FR-OTA-12 (clasificador) — núcleo puro de la política OTA (FSD §7, §12),
 * con los casos de los contratos de §7.4 y §12.3. Un ejecutable por TC (argv[1]). */
#include <stdio.h>
#include <string.h>
#include "ota_politica.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)
#define M(x) ota_motivo_texto(x)
#define REPO "https://github.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/"

static ota_motivo_t pay(const char *j, char *url) { return ota_payload(j, strlen(j), url, OTA_URL_MAX + 1); }

static void tc_ota_01(void)
{
    char url[OTA_URL_MAX + 1];
    ESPERA(pay("{\"url\":\"" REPO "v0.0.1/f.bin\"}", url) == OTA_OK && strcmp(url, REPO "v0.0.1/f.bin") == 0, "válido: %s", url);
    ESPERA(pay(" { \"url\" : \"https:\\/\\/x\" } ", url) == OTA_OK && strcmp(url, "https://x") == 0, "escape \\/ y blancos: %s", url);
    /* §12.3: {}, {"url":5}, no-json, URL de 513 bytes, clave extra */
    const char *malos[] = {"{}", "{\"url\":5}", "no-json", "{\"url\":\"x\",\"x\":1}", "{\"x\":1,\"url\":\"x\"}",
                           "{\"url\":\"\"}", "{\"URL\":\"x\"}", "[\"x\"]", "{\"url\":\"x\"} basura", "{\"url\":\"x\\u0041\"}",
                           "{\"url\":\"a\nb\"}", "{\"url\":\"x\"", "", "{\"url\":null}"};
    for (size_t i = 0; i < sizeof malos / sizeof malos[0]; i++)
        ESPERA(pay(malos[i], url) == OTA_RECHAZADO_PAYLOAD, "aceptado: %s", malos[i]);
    char largo[600] = "{\"url\":\"";
    memset(largo + 8, 'a', 513); strcpy(largo + 8 + 513, "\"}");
    ESPERA(pay(largo, url) == OTA_RECHAZADO_PAYLOAD, "URL de 513 bytes aceptada");
    largo[8 + 512] = '"'; largo[8 + 513] = '}'; largo[8 + 514] = '\0';
    ESPERA(pay(largo, url) == OTA_OK && strlen(url) == 512, "URL de 512 bytes rechazada");
    ESPERA(strcmp(M(OTA_RECHAZADO_PAYLOAD), "rechazado:payload") == 0, "texto");
}

static void tc_ota_02(void)
{
    bool prueba;
    /* válida, en las dos imágenes */
    ESPERA(ota_url_inicial(REPO "v0.0.1/firmware_v0.0.1.bin", false, &prueba) == OTA_OK && !prueba, "v* en producción");
    ESPERA(ota_url_inicial(REPO "v0.0.1/firmware_v0.0.1.bin", true, &prueba) == OTA_OK && !prueba, "v* en banco");
    ESPERA(ota_url_inicial("https://GitHub.com:443/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x.bin", false, &prueba) == OTA_OK,
           "host en mayúsculas y :443");
    /* FR-OTA-02 (§7.4): http://, host ajeno */
    ESPERA(ota_url_inicial("http://github.com/x", false, &prueba) == OTA_RECHAZADO_HOST, "http");
    ESPERA(ota_url_inicial("https://evil.example/x", false, &prueba) == OTA_RECHAZADO_HOST, "host ajeno");
    /* FR-OTA-11 (§7.4) */
    ESPERA(ota_url_inicial("https://github.com/otro/repo/releases/download/v1/x.bin", false, &prueba) == OTA_RECHAZADO_RUTA, "otro repo");
    ESPERA(ota_url_inicial("https://github.com/rafaelrodWebpos/villa-nodo-clima-piloto/archive/x", false, &prueba) == OTA_RECHAZADO_RUTA, "archive");
    ESPERA(ota_url_inicial(REPO, false, &prueba) == OTA_RECHAZADO_RUTA, "solo el prefijo");
    ESPERA(ota_url_inicial("https://release-assets.githubusercontent.com" "/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x", false, &prueba) == OTA_RECHAZADO_RUTA,
           "URL inicial de release-assets (§7.3: solo la de github.com)");
    /* FR-OTA-13: ota-test-* solo en banco, y marcada como prueba */
    ESPERA(ota_url_inicial(REPO "ota-test-b1/x.bin", false, &prueba) == OTA_RECHAZADO_RUTA, "ota-test en producción");
    ESPERA(ota_url_inicial(REPO "ota-test-b1/x.bin", true, &prueba) == OTA_OK && prueba, "ota-test en banco");
    /* FR-OTA-14 (§7.4): usuario@, :8443, %2e, /../, \, mayúsculas en el esquema, control, sufijo extra */
    const struct { const char *url; ota_motivo_t m; } c14[] = {
        {"https://user@github.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x", OTA_RECHAZADO_HOST},
        {"https://github.com@evil.example/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x", OTA_RECHAZADO_HOST},
        {"https://github.com:8443/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x", OTA_RECHAZADO_HOST},
        {"https://github.com:/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x", OTA_RECHAZADO_HOST},
        {"https://git%68ub.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x", OTA_RECHAZADO_HOST},
        {REPO "v1/%2e%2e/x", OTA_RECHAZADO_RUTA},
        {REPO "v1/../../../otro/x", OTA_RECHAZADO_RUTA},
        {REPO "./v1/x", OTA_RECHAZADO_RUTA},
        {REPO "v1\\x", OTA_RECHAZADO_RUTA},
        {"HTTPS://github.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x", OTA_RECHAZADO_HOST},
        {"https://github.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x\x01", OTA_RECHAZADO_RUTA},
        {"https://github.com\t/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x", OTA_RECHAZADO_HOST},
        {"https://github.com.evil.example/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x", OTA_RECHAZADO_HOST},
        {"https://github.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x#frag", OTA_RECHAZADO_RUTA},
        {"https://github.com", OTA_RECHAZADO_HOST},
        {"https:///rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x", OTA_RECHAZADO_HOST},
        {"https://github.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/v1/x\xc3\xa9", OTA_RECHAZADO_RUTA},
    };
    for (size_t i = 0; i < sizeof c14 / sizeof c14[0]; i++) {
        ota_motivo_t m = ota_url_inicial(c14[i].url, true, &prueba);
        ESPERA(m == c14[i].m, "FR-OTA-14 caso %zu: %s, esperado %s", i, M(m), M(c14[i].m));
    }
    /* redirecciones (FR-OTA-02, T20): la de release-assets con su consulta firmada vale */
    const char *ra = "https://release-assets.githubusercontent.com/github-production-release-asset/1/2?sp=r&sv=2018&se=2026-11-10T22%3A00%3A00Z&sig=a%2Bb";
    ESPERA(ota_url_redireccion(ra, 1) == OTA_OK, "release-assets con consulta firmada");
    ESPERA(ota_url_redireccion("https://objects.githubusercontent.com/x", 1) == OTA_RECHAZADO_HOST, "objects.githubusercontent.com (§7.3)");
    ESPERA(ota_url_redireccion("http://release-assets.githubusercontent.com/x", 1) == OTA_RECHAZADO_HOST, "salto a http");
    ESPERA(ota_url_redireccion("https://release-assets.githubusercontent.com/a/../b", 2) == OTA_RECHAZADO_HOST, "salto con .. → rechazado:host (T20)");
    ESPERA(ota_url_redireccion(ra, 3) == OTA_OK, "tercera redirección");
    ESPERA(ota_url_redireccion(ra, 4) == OTA_ERROR_REDIRECCIONES, "cuarta redirección");
}

static void tc_ota_03(void)
{
    /* §7.4: (en ejecución, destino) para v* y ota-test en banco */
    ESPERA(ota_version("1.2.0", "1.1.9", false) == OTA_RECHAZADO_VERSION_ANTERIOR, "1.1.9 < 1.2.0");
    ESPERA(ota_version("1.2.0", "1.2.0", false) == OTA_RECHAZADO_MISMA_VERSION, "misma");
    ESPERA(ota_version("1.2.0", "1.2.1", false) == OTA_OK, "1.2.1");
    ESPERA(ota_version("1.2.0", "0.0.1", true) == OTA_OK, "ota-test fuera del anti-downgrade (H-84)");
    ESPERA(ota_version("0.0.1", "0.0.1", true) == OTA_RECHAZADO_MISMA_VERSION, "ota-test misma versión");
    /* semver: pre-release antes que la versión final; imagen de banco < primer tag */
    ESPERA(ota_version("0.0.0-89a9f7b-bench", "0.0.1", false) == OTA_OK, "imagen de banco → v0.0.1");
    ESPERA(ota_version("0.0.1", "0.0.1-rc.1", false) == OTA_RECHAZADO_VERSION_ANTERIOR, "rc es anterior");
    ESPERA(ota_version("0.0.1-rc.2", "0.0.1-rc.10", false) == OTA_OK, "rc.10 > rc.2 (numérico)");
    ESPERA(ota_version("1.10.0", "1.9.9", false) == OTA_RECHAZADO_VERSION_ANTERIOR, "1.9.9 < 1.10.0 (numérico)");
    ESPERA(ota_version("v1.2.0", "1.2.1", false) == OTA_OK, "prefijo v");
    ESPERA(ota_version("1.2.0", "1.2.0+build5", false) == OTA_RECHAZADO_MISMA_VERSION, "+build no cuenta");
    /* destino que no es semver: error:imagen */
    const char *malas[] = {"", "1.2", "01.2.0", "1.2.0-", "x.y.z", "1.2.0 ", "1.2.0-a b"};
    for (size_t i = 0; i < sizeof malas / sizeof malas[0]; i++)
        ESPERA(ota_version("1.2.0", malas[i], false) == OTA_ERROR_IMAGEN, "versión «%s» aceptada", malas[i]);
}

static void tc_ota_04(void)
{
    /* §7.4: DNS, TCP, timeout, 404, 500 → red, red, red, http, http */
    ESPERA(ota_clasificar_fallo(OTA_FALLO_DNS, 0) == OTA_ERROR_RED, "dns");
    ESPERA(ota_clasificar_fallo(OTA_FALLO_TCP, 0) == OTA_ERROR_RED, "tcp");
    ESPERA(ota_clasificar_fallo(OTA_FALLO_TIMEOUT, 0) == OTA_ERROR_RED, "timeout");
    ESPERA(ota_clasificar_fallo(OTA_FALLO_HTTP, 404) == OTA_ERROR_HTTP, "404");
    ESPERA(ota_clasificar_fallo(OTA_FALLO_HTTP, 500) == OTA_ERROR_HTTP, "500");
    ESPERA(ota_clasificar_fallo(OTA_FALLO_HTTP, 200) == OTA_OK, "200 no es fallo");
    ESPERA(ota_clasificar_fallo(OTA_FALLO_TLS, 0) == OTA_ERROR_TLS, "tls");
    ESPERA(strcmp(M(OTA_ERROR_RED), "error:red") == 0 && strcmp(M(OTA_RECHAZADO_VERSION_ANTERIOR), "rechazado:version_anterior") == 0, "textos §9.3");
}

int main(int argc, char **argv)
{
    const char *tc = argc > 1 ? argv[1] : "todos";
    if (!strcmp(tc, "TC-OTA-01") || !strcmp(tc, "todos")) tc_ota_01();
    if (!strcmp(tc, "TC-OTA-02") || !strcmp(tc, "todos")) tc_ota_02();
    if (!strcmp(tc, "TC-OTA-03") || !strcmp(tc, "todos")) tc_ota_03();
    if (!strcmp(tc, "TC-OTA-04") || !strcmp(tc, "todos")) tc_ota_04();
    printf("%s: %s\n", tc, fallos ? "FALLO" : "ok");
    return fallos != 0;
}
