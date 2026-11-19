/* L2 ota — turno de la descarga (A3-03, B-1). Núcleo puro; el adaptador lo usa bajo su cerrojo. */
#include "ota_turno.h"

bool ota_turno_tomar(ota_turno_t *t)
{
    if (!t || t->activa) return false;
    t->activa = true;
    t->abortada = t->completada = false;
    return true;
}

ota_aborto_t ota_turno_abortar(ota_turno_t *t)
{
    if (!t) return OTA_ABORTO_NADA;
    if (t->completada) { t->completada = false; return OTA_ABORTO_TARDE; }
    if (!t->activa) return OTA_ABORTO_NADA;
    t->abortada = true;
    return OTA_ABORTO_EN_CURSO;
}

bool ota_turno_puede_finalizar(const ota_turno_t *t)
{
    return t && t->activa && !t->abortada;
}

ota_cierre_t ota_turno_cerrar(ota_turno_t *t, bool imagen_escrita)
{
    if (!t) return OTA_CIERRE_CALLAR;
    if (t->abortada) return imagen_escrita ? OTA_CIERRE_RESTAURAR : OTA_CIERRE_CALLAR;
    t->completada = imagen_escrita;
    return OTA_CIERRE_AVISAR;
}

void ota_turno_soltar(ota_turno_t *t)
{
    if (t) t->activa = t->abortada = false;
}
