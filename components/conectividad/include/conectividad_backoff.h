/* L2 conectividad — backoff de reintentos (FSD §6.5, FR-CON-02). Núcleo puro:
 * 1 s, se duplica en cada fallo, techo de 60 s; vuelve a 1 s tras cada éxito. */
#pragma once

typedef struct { unsigned fallos; } con_backoff_t;

void con_backoff_reiniciar(con_backoff_t *b);
/* Registra un fallo y devuelve la espera hasta el siguiente intento, en ms */
unsigned con_backoff_fallo(con_backoff_t *b);
