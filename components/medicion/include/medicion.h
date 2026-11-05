/* L2 medicion — núcleo puro del ciclo de medición (FSD §5): punto de rocío
 * (FR-MED-03), «no publicar punto_rocio» (FR-MED-04), redondeo a 1 decimal
 * (FR-MED-05) y la línea E3 de §18. Sin ESP-IDF; lo compila tests/host. */
#pragma once
#include <stdbool.h>
#include <stddef.h>

#define MED_LINEA_MAX 64

typedef struct {
    bool valida;        /* la lectura del SHT41 fue válida (FR-SEN-02) */
    bool td_valida;     /* hay punto de rocío que publicar (FR-MED-04) */
    float t, hr, td;    /* redondeados a 1 decimal (FR-MED-05) */
    double td_crudo;    /* Td sin redondear (para FR-MED-03) */
} med_lectura_t;

/* Redondeo a 1 decimal, alejando de cero los empates; nunca devuelve −0 */
float med_redondear1(float x);

/* De una lectura (válida o no) a lo que publica el ciclo */
med_lectura_t med_procesar(bool valida, float t, float hr);

/* E3: «med: T=<t> HR=<h> Td=<td|->» o «med: invalida (<motivo>)» */
void med_linea(char *buf, size_t cap, const med_lectura_t *m, const char *motivo);
