/* L0 udplog — envío con reintento (FR-LOG-02, FR-LOG-03; H-57). Núcleo puro. */
#include "udplog_envio.h"

bool udplog_enviar(udplog_envio_t *e, const char *linea, size_t n)
{
    for (int intento = 0; intento <= UDPLOG_REINTENTOS; intento++) {
        if (intento) e->esperar(UDPLOG_ESPERA_MS, e->ctx);
        if (e->enviar(linea, n, e->ctx) >= 0) {
            if (intento) e->reintentadas++;
            return true;
        }
    }
    e->descartadas++;
    return false;
}
