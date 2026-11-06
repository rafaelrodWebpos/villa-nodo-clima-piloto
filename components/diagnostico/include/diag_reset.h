/* L1 diagnostico — nombre de la causa del último reinicio: campo `reset` de
 * `status` (§9.3, FR-MQTT-08) y `reset=<causa>` de la línea E1 (§18). Núcleo
 * puro; el adaptador traduce esp_reset_reason() a diag_reset_t. */
#pragma once

typedef enum {
    DIAG_RESET_OTRO = 0, DIAG_RESET_POWERON, DIAG_RESET_EXT, DIAG_RESET_SW, DIAG_RESET_PANIC,
    DIAG_RESET_TASK_WDT, DIAG_RESET_INT_WDT, DIAG_RESET_WDT, DIAG_RESET_DEEPSLEEP,
    DIAG_RESET_BROWNOUT, DIAG_RESET_USB, DIAG_RESET_JTAG, DIAG_RESET_N
} diag_reset_t;

const char *diag_reset_nombre(diag_reset_t c);
