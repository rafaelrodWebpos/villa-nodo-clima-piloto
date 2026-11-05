/* TC-SEN-01 · FR-SEN-01 y TC-SEN-02 · FR-SEN-02 (host): conversión y CRC de la
 * trama del SHT41 (FSD §8.1, §8.3). Un ejecutable por test: argv[1] elige. */
#include <math.h>
#include <stdio.h>
#include <string.h>
#include "sht41_trama.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

/* Trama de 6 bytes con los CRC correctos, calculados aquí de forma independiente */
static uint8_t crc_ref(uint8_t a, uint8_t b)
{
    uint8_t c = 0xFF, d[2] = {a, b};
    for (int i = 0; i < 2; i++) {
        c ^= d[i];
        for (int k = 0; k < 8; k++) c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x31) : (uint8_t)(c << 1);
    }
    return c;
}
static void trama(uint16_t st, uint16_t srh, uint8_t f[6])
{
    f[0] = st >> 8; f[1] = st & 0xFF; f[2] = crc_ref(f[0], f[1]);
    f[3] = srh >> 8; f[4] = srh & 0xFF; f[5] = crc_ref(f[3], f[4]);
}

static void sen01(void)
{
    /* Vector de la hoja de datos de Sensirion: CRC(0xBEEF) = 0x92 */
    const uint8_t beef[2] = {0xBE, 0xEF};
    ESPERA(sht41_crc8(beef, 2) == 0x92, "crc(0xBEEF) = 0x%02x", sht41_crc8(beef, 2));
    const struct { uint16_t st, srh; float t, hr; } v[] = {
        {0, 0, -45.00f, 0.00f},            /* HR = -6 recortada a 0 */
        {65535, 65535, 130.00f, 100.00f},  /* HR = 119 recortada a 100 */
        {0x6666, 0x8000, 25.00f, 56.50f},
    };
    for (size_t i = 0; i < sizeof v / sizeof *v; i++) {
        uint8_t f[6]; float t = NAN, hr = NAN;
        trama(v[i].st, v[i].srh, f);
        sht41_resultado_t r = sht41_decodificar(f, &t, &hr);
        ESPERA(r == SHT41_OK, "vector %zu: resultado %d", i, r);
        ESPERA(fabsf(t - v[i].t) < 0.005f, "vector %zu: T = %.4f, esperado %.2f", i, t, v[i].t);
        ESPERA(fabsf(hr - v[i].hr) < 0.005f, "vector %zu: HR = %.4f, esperado %.2f", i, hr, v[i].hr);
        ESPERA(hr >= 0.0f && hr <= 100.0f, "vector %zu: HR fuera de [0, 100]: %.4f", i, hr);
    }
    printf("TC-SEN-01: %s\n", fallos ? "FALLO" : "ok");
}

static void sen02(void)
{
    for (int mitad = 0; mitad < 2; mitad++) {
        uint8_t f[6]; float t = 123.0f, hr = 456.0f;
        trama(0x6666, 0x8000, f);
        f[mitad ? 5 : 2] ^= 0x01;           /* CRC de T o de HR alterado */
        sht41_resultado_t r = sht41_decodificar(f, &t, &hr);
        ESPERA(r == SHT41_ERR_CRC, "CRC de %s alterado: resultado %d", mitad ? "HR" : "T", r);
        /* Prohibido: que la mitad válida salga sola; las salidas no se tocan */
        ESPERA(t == 123.0f && hr == 456.0f, "CRC de %s alterado: T=%.2f HR=%.2f escritas", mitad ? "HR" : "T", t, hr);
    }
    /* Un dato alterado (no el CRC) también es inválido */
    uint8_t f[6]; float t, hr;
    trama(0x6666, 0x8000, f);
    f[0] ^= 0x80;
    ESPERA(sht41_decodificar(f, &t, &hr) == SHT41_ERR_CRC, "dato de T alterado aceptado");
    ESPERA(strcmp(sht41_motivo(SHT41_ERR_CRC), "crc") == 0 && strcmp(sht41_motivo(SHT41_ERR_NACK), "nack") == 0 &&
           strcmp(sht41_motivo(SHT41_ERR_TIMEOUT), "timeout") == 0, "motivos de E3 distintos de nack|timeout|crc");
    printf("TC-SEN-02: %s\n", fallos ? "FALLO" : "ok");
}

int main(int argc, char **argv)
{
    if (argc > 1 && strcmp(argv[1], "sen02") == 0) sen02(); else sen01();
    return fallos != 0;
}
