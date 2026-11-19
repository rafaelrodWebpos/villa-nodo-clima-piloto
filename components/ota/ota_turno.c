/* L2 ota — turno de la descarga (A3-03). Núcleo puro; el adaptador lo usa bajo su cerrojo. */
#include "ota_turno.h"

bool ota_turno_tomar(ota_turno_t *t)
{
    if (!t || t->activa) return false;
    t->activa = true;
    t->abortada = false;
    return true;
}

void ota_turno_abortar(ota_turno_t *t)
{
    if (t && t->activa) t->abortada = true;
}

bool ota_turno_avisar(const ota_turno_t *t)
{
    return t && t->activa && !t->abortada;
}

void ota_turno_soltar(ota_turno_t *t)
{
    if (t) t->activa = t->abortada = false;
}
