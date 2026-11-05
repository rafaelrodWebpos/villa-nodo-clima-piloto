/* L1 sht41 — núcleo puro de la trama (FSD §8.1; FR-SEN-01, FR-SEN-02). */
#include "sht41_trama.h"

uint8_t sht41_crc8(const uint8_t *d, size_t n)
{
    uint8_t crc = 0xFF;
    for (size_t i = 0; i < n; i++) {
        crc ^= d[i];
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x31) : (uint8_t)(crc << 1);
    }
    return crc;
}

sht41_resultado_t sht41_decodificar(const uint8_t f[6], float *t, float *hr)
{
    /* FR-SEN-02: un CRC malo invalida las dos mitades */
    if (sht41_crc8(f, 2) != f[2] || sht41_crc8(f + 3, 2) != f[5]) return SHT41_ERR_CRC;
    uint16_t st = (uint16_t)(f[0] << 8 | f[1]), srh = (uint16_t)(f[3] << 8 | f[4]);
    float h = -6.0f + 125.0f * (float)srh / 65535.0f;
    *t = -45.0f + 175.0f * (float)st / 65535.0f;
    *hr = h < 0.0f ? 0.0f : h > 100.0f ? 100.0f : h;
    return SHT41_OK;
}

const char *sht41_motivo(sht41_resultado_t r)
{
    switch (r) {
    case SHT41_ERR_NACK:    return "nack";
    case SHT41_ERR_TIMEOUT: return "timeout";
    case SHT41_ERR_CRC:     return "crc";
    default:                return "ok";
    }
}
