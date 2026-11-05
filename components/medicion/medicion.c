/* L2 medicion — núcleo puro del ciclo de medición (FSD §5.4). */
#include "medicion.h"
#include <math.h>
#include <stdio.h>

#define MAGNUS_B 17.62     /* Apéndice A, constantes de Sonntag */
#define MAGNUS_C 243.12

float med_redondear1(float x)
{
    /* En doble: 21.45f vale 21.4500007…, así que ×10 da 214.50000… y round()
     * aleja el empate de cero (FR-MED-05). Un −0 sale como 0. */
    double r = round((double)x * 10.0) / 10.0;
    return r == 0.0 ? 0.0f : (float)r;
}

med_lectura_t med_procesar(bool valida, float t, float hr)
{
    med_lectura_t m = {0};
    if (!valida) return m;                            /* FR-SEN-02: nada que publicar */
    m.valida = true;
    m.t = med_redondear1(t);
    m.hr = med_redondear1(hr);
    if (hr > 0.0f) {                                  /* FR-MED-04: HR ≤ 0 → sin Td */
        double g = log((double)hr / 100.0) + (MAGNUS_B * t) / (MAGNUS_C + t);
        m.td_crudo = MAGNUS_C * g / (MAGNUS_B - g);
        if (isfinite(m.td_crudo)) {
            m.td_valida = true;
            m.td = med_redondear1((float)m.td_crudo);
        }
    }
    return m;
}

void med_linea(char *buf, size_t cap, const med_lectura_t *m, const char *motivo)
{
    if (!buf || cap == 0) return;
    if (!m->valida) { snprintf(buf, cap, "med: invalida (%s)", motivo ? motivo : "nack"); return; }
    if (m->td_valida) snprintf(buf, cap, "med: T=%.1f HR=%.1f Td=%.1f", m->t, m->hr, m->td);
    else              snprintf(buf, cap, "med: T=%.1f HR=%.1f Td=-", m->t, m->hr);
}
