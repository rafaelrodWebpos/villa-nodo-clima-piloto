/* L1 diagnostico — nombres de §9.3 (FSD 0.9.4) para el campo `reset` (FR-MQTT-08) y E1. */
#include "diag_reset.h"

static const char *const NOMBRE[DIAG_RESET_N] = {
    [DIAG_RESET_OTRO] = "otro",           [DIAG_RESET_POWERON] = "poweron",
    [DIAG_RESET_EXT] = "ext",             [DIAG_RESET_SW] = "sw",
    [DIAG_RESET_PANIC] = "panic",         [DIAG_RESET_TASK_WDT] = "task_wdt",
    [DIAG_RESET_INT_WDT] = "int_wdt",     [DIAG_RESET_WDT] = "wdt",
    [DIAG_RESET_DEEPSLEEP] = "deepsleep", [DIAG_RESET_BROWNOUT] = "brownout",
    [DIAG_RESET_USB] = "usb",             [DIAG_RESET_JTAG] = "jtag",
};

const char *diag_reset_nombre(diag_reset_t c)
{
    return ((int)c >= 0 && c < DIAG_RESET_N) ? NOMBRE[c] : "otro";
}
