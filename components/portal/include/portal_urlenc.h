/* L1 portal — cuerpo application/x-www-form-urlencoded del envío (FR-POR-04).
 * Núcleo puro. */
#pragma once
#include "portal_form.h"

/* Decodifica body en el sitio («k=v&k=v», '+' = espacio, %XX) y deja en v[]
 * punteros a los valores de los campos de §17; los ausentes quedan en NULL y
 * las claves desconocidas se ignoran. Si una clave se repite, cuenta la
 * primera. Un %XX mal formado se conserva literal. */
void portal_decodificar(char *body, const char *v[PORTAL_N_CAMPOS]);
