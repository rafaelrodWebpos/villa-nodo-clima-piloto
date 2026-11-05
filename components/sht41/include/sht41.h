/* L1 sht41 — adaptador I²C del SHT41 (FSD §8.1, C-HW-04, C-HW-05): SDA=GPIO8,
 * SCL=GPIO9, 100 kHz, dirección 0x44, medida 0xFD sin calentador. */
#pragma once
#include "esp_err.h"
#include "sht41_trama.h"

esp_err_t sht41_iniciar(void);

/* Una medida completa: comando, ≥ 10 ms reales de conversión y lectura de la
 * trama. NACK, timeout de I²C y CRC malo devuelven su error (FR-SEN-02). */
sht41_resultado_t sht41_leer(float *t, float *hr);
