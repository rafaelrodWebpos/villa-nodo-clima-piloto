/*
 * i2c_probe — firmware de prueba del bus del SHT41.
 *
 * 1. Escanea el bus en SDA=GPIO8, SCL=GPIO9, 100 kHz (C-HW-04/05) y emite la
 *    línea E12 de §18: «i2c: scan sda=8 scl=9 hz=100000 ack=<lista|ninguno>».
 * 2. Cada 2 s lee el SHT41 (0x44, comando 0xFD, §8.1) y emite una línea con el
 *    formato E3 de §18: «med: T=<t> HR=<h> Td=-» o «med: invalida (<motivo>)».
 *    Es el latido que observa el banco: sirve en cualquier momento, también
 *    para el corte de SDA del operador (agenda, fila 3).
 */
#include <stdio.h>
#include <string.h>
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define PIN_SDA 8
#define PIN_SCL 9
#define BUS_HZ 100000
#define SHT41_ADDR 0x44
#define SHT41_MEASURE_HIGH 0xFD
#define XFER_TIMEOUT_MS 50

static i2c_master_bus_handle_t bus;
static i2c_master_dev_handle_t sht41;

static uint8_t crc8(const uint8_t *d, int n)
{
    uint8_t crc = 0xFF;                       /* §8.1: poly 0x31, init 0xFF */
    for (int i = 0; i < n; i++) {
        crc ^= d[i];
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x80) ? (uint8_t)((crc << 1) ^ 0x31) : (uint8_t)(crc << 1);
    }
    return crc;
}

static int cur_sda = PIN_SDA, cur_scl = PIN_SCL;

static void scan(void)
{
    char list[256] = "";
    for (uint16_t a = 0x08; a < 0x78; a++) {
        if (i2c_master_probe(bus, a, XFER_TIMEOUT_MS) == ESP_OK) {
            char item[8];
            snprintf(item, sizeof item, "%s0x%02x", list[0] ? "," : "", a);
            strncat(list, item, sizeof list - strlen(list) - 1);
        }
    }
    ESP_LOGI("i2c", "scan sda=%d scl=%d hz=%d ack=%s",
             cur_sda, cur_scl, BUS_HZ, list[0] ? list : "ninguno");
}

/* Diagnóstico del cableado: nivel en reposo de SDA/SCL sin pull interno y con
 * él. Con pull-ups externos ambos leen 1 sin pull interno; un 0 sin pull que
 * pasa a 1 con él dice que faltan los pull-ups; un 0 en ambos casos, línea a
 * masa o sensor sin alimentar sujetándola. */
static void idle_levels(void)
{
    const gpio_num_t pins[2] = {PIN_SDA, PIN_SCL};
    int lv[2][2];
    for (int pull = 0; pull < 2; pull++) {
        for (int i = 0; i < 2; i++) {
            gpio_reset_pin(pins[i]);
            gpio_set_direction(pins[i], GPIO_MODE_INPUT);
            gpio_set_pull_mode(pins[i], pull ? GPIO_PULLUP_ONLY : GPIO_FLOATING);
        }
        vTaskDelay(pdMS_TO_TICKS(5));
        for (int i = 0; i < 2; i++) lv[pull][i] = gpio_get_level(pins[i]);
    }
    ESP_LOGI("i2c", "idle sin_pull sda=%d scl=%d con_pull sda=%d scl=%d",
             lv[0][0], lv[0][1], lv[1][0], lv[1][1]);
    for (int i = 0; i < 2; i++) gpio_reset_pin(pins[i]);
}

static const char *why(esp_err_t e)
{
    return e == ESP_ERR_TIMEOUT ? "timeout" : "nack";
}

static void read_once(void)
{
    uint8_t cmd = SHT41_MEASURE_HIGH, rx[6];
    esp_err_t e = i2c_master_transmit(sht41, &cmd, 1, XFER_TIMEOUT_MS);
    if (e == ESP_OK) {
        vTaskDelay(pdMS_TO_TICKS(10));
        e = i2c_master_receive(sht41, rx, sizeof rx, XFER_TIMEOUT_MS);
    }
    if (e != ESP_OK) {
        ESP_LOGW("med", "invalida (%s)", why(e));
        i2c_master_bus_reset(bus);            /* que un corte no bloquee el bus */
        return;
    }
    if (crc8(rx, 2) != rx[2] || crc8(rx + 3, 2) != rx[5]) {
        ESP_LOGW("med", "invalida (crc)");
        return;
    }
    uint16_t st = (uint16_t)(rx[0] << 8 | rx[1]), srh = (uint16_t)(rx[3] << 8 | rx[4]);
    float t = -45.0f + 175.0f * st / 65535.0f;
    float h = -6.0f + 125.0f * srh / 65535.0f;
    if (h < 0) h = 0;
    if (h > 100) h = 100;
    ESP_LOGI("med", "T=%.2f HR=%.2f Td=-", t, h);
}

static void open_bus_on(int sda, int scl, bool internal_pullup)
{
    if (bus) {
        i2c_master_bus_rm_device(sht41);
        i2c_del_master_bus(bus);
        bus = NULL;
    }
    cur_sda = sda;
    cur_scl = scl;
    i2c_master_bus_config_t bc = {
        .i2c_port = -1,
        .sda_io_num = sda,
        .scl_io_num = scl,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = internal_pullup,
    };
    ESP_ERROR_CHECK(i2c_new_master_bus(&bc, &bus));
    i2c_device_config_t dc = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = SHT41_ADDR,
        .scl_speed_hz = BUS_HZ,
    };
    ESP_ERROR_CHECK(i2c_master_bus_add_device(bus, &dc, &sht41));
}

static void open_bus(bool internal_pullup)
{
    open_bus_on(PIN_SDA, PIN_SCL, internal_pullup);
}

void app_main(void)
{
    ESP_LOGI("probe", "i2c_probe");
    idle_levels();
    /* Diagnóstico: el mismo escaneo con el pull-up interno (~45 kΩ). No cuenta
     * para C-HW-05, que exige pull-ups externos. */
    esp_log_level_set("i2c.master", ESP_LOG_NONE);
    open_bus(true);
    ESP_LOGI("i2c", "diagnostico: escaneo con pull-up interno");
    scan();
    ESP_LOGI("i2c", "diagnostico: SDA y SCL cruzados, pull-up interno");
    open_bus_on(PIN_SCL, PIN_SDA, true);
    scan();
    /* El escaneo que cuenta (E12): solo pull-ups externos. */
    open_bus(false);
    scan();
    ESP_LOGI("probe", "Init complete");
    for (;;) {
        read_once();
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
}
