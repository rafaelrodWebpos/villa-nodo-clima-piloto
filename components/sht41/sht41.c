/* L1 sht41 — adaptador I²C (FSD §8.1). La trama la decodifica sht41_trama.c. */
#include "sht41.h"
#include "driver/i2c_master.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define PIN_SDA 8               /* C-HW-04 (D1) */
#define PIN_SCL 9
#define BUS_HZ 100000           /* C-HW-05 */
#define DIRECCION 0x44
#define CMD_MEDIDA_ALTA 0xFD
#define TIMEOUT_MS 50

static i2c_master_bus_handle_t s_bus;
static i2c_master_dev_handle_t s_dev;

esp_err_t sht41_iniciar(void)
{
    i2c_master_bus_config_t bc = {
        .i2c_port = -1,
        .sda_io_num = PIN_SDA,
        .scl_io_num = PIN_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false,   /* C-HW-05: pull-ups externos */
    };
    esp_err_t e = i2c_new_master_bus(&bc, &s_bus);
    if (e != ESP_OK) return e;
    i2c_device_config_t dc = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = DIRECCION,
        .scl_speed_hz = BUS_HZ,
    };
    /* Un NACK es un resultado de la medida (E3), no un error que loguear aparte */
    esp_log_level_set("i2c.master", ESP_LOG_NONE);
    return i2c_master_bus_add_device(s_bus, &dc, &s_dev);
}

sht41_resultado_t sht41_leer(float *t, float *hr)
{
    if (!s_dev) return SHT41_ERR_NACK;
    uint8_t cmd = CMD_MEDIDA_ALTA, rx[6];
    esp_err_t e = i2c_master_transmit(s_dev, &cmd, 1, TIMEOUT_MS);
    if (e == ESP_OK) {
        /* ≥ 10 ms reales (§8.1): pdMS_TO_TICKS(10) puede ser un tick que dure
         * casi 0 ms si la tarea está a mitad de tick; uno más lo garantiza
         * (consecuencia de sht41-wiring en el plan, sonda de fd2dbf7). */
        vTaskDelay(pdMS_TO_TICKS(10) + 1);
        e = i2c_master_receive(s_dev, rx, sizeof rx, TIMEOUT_MS);
    }
    if (e != ESP_OK) {
        i2c_master_bus_reset(s_bus);          /* que un corte de SDA no deje el bus colgado */
        return e == ESP_ERR_TIMEOUT ? SHT41_ERR_TIMEOUT : SHT41_ERR_NACK;
    }
    return sht41_decodificar(rx, t, hr);
}
