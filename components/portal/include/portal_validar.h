/* L1 portal — validador de §17 (FR-POR-04, D11, D23). Núcleo puro. */
#pragma once
#include "portal_form.h"

typedef struct {
    const char *error[PORTAL_N_CAMPOS];   /* mensaje visible por campo, o NULL si es válido */
    int n_errores;
} portal_validacion_t;

/* Valida los valores recibidos (NUL-terminados; NULL = campo ausente, que
 * cuenta como vacío) con las reglas de §17. No modifica nada más. */
void portal_validar(const char *const v[PORTAL_N_CAMPOS], portal_validacion_t *out);
