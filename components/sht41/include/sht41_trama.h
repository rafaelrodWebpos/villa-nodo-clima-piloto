/* L1 sht41 — núcleo puro: CRC y conversión de la trama de 6 bytes (FSD §8.1,
 * FR-SEN-01, FR-SEN-02). Sin ESP-IDF; lo compila también tests/host. */
#pragma once
#include <stddef.h>
#include <stdint.h>

typedef enum { SHT41_OK = 0, SHT41_ERR_NACK, SHT41_ERR_TIMEOUT, SHT41_ERR_CRC } sht41_resultado_t;

/* CRC-8 de Sensirion: polinomio 0x31, valor inicial 0xFF, sin XOR final */
uint8_t sht41_crc8(const uint8_t *d, size_t n);

/* Comprueba los dos CRC y convierte: T = −45 + 175·S_T/65535 °C,
 * HR = −6 + 125·S_RH/65535 % recortada a [0, 100]. Si un CRC falla, la lectura
 * entera es inválida (SHT41_ERR_CRC) y *t y *hr no se tocan. */
sht41_resultado_t sht41_decodificar(const uint8_t trama[6], float *t, float *hr);

/* Motivo de la línea E3 «med: invalida (<nack|timeout|crc>)» */
const char *sht41_motivo(sht41_resultado_t r);
