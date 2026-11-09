# TC-WDT-01 — reevaluación con la detección de reinicios de H-78 (sin repetir las 24 h)

- Evidencia: esta carpeta (`TC-WDT-01.md`, `TC-WDT-01-serie.log`, `TC-WDT-01-mqtt.log`), 24 h
  sobre `0.0.0-17dc543-bench` con el fork villa-1 y la salida a Internet apagada.
- Comprobación nueva: commit d212ffa (`tests/bench/consola.py`, test de host
  `tests/host/test_consola.py` en la CI, run 42692818936).
- Se aplica `quitar_relecturas` y `reinicios` al log serie guardado. Este log no conserva la
  marca del banco; la ventana se sitúa con el resultado registrado: las líneas del arranque
  original (46, 47 y 72) no las señaló la ejecución, así que quedaron antes de la ventana.

## Resultado de la comprobación nueva

| Aserción | Valor | Veredicto |
|---|---|---|
| Relecturas del banco | 1 bloque: líneas 113–179 (67 líneas), copia idéntica de las 46–112; tras quitarla el reloj sigue de `I (4115)` a `I (4125)` | descartada |
| Retrocesos del reloj de esp_log | 1, en la línea 23 (`I (27) boot: ESP-IDF …`): el reset previsto tras el aprovisionamiento, anterior a la línea 46, fuera de la ventana | PASS (0 en la ventana) |
| Reloj de esp_log al final | 86 460 615 ms, sin retrocesos; coincide con uptime_s = 86460 del último status | PASS |
| uptime_s creciente | 4 → 86460 en los 1422 status, ninguno no creciente | PASS |
| reset sin cambio | ['usb'] | PASS |
| task_wdt | 0 líneas | PASS |
| 5 cortes hechos | broker 7203 s, wifi 21612 s, broker 36022 s, wifi 50429 s, broker 64808 s | PASS |
| recuperación ≤ 150 s | 3,4 / 26,1 / 3,5 / 26,0 / 3,3 s | PASS |
| Δlecturas = ciclos ± 2 | 1441 en 1441 ciclos (86 456 s) | PASS |
| publicaciones por medida = ciclos en OPERATIVO ± 2 | 1421 / 1421 / 1421 con 1421 | PASS |
| control de consola | 1440 med: en la ventana, ningún tramo de 10 min con < 5 | PASS |

**Resultado: PASS** (reevaluación).

## Observación del banco

El bloque repetido sale tras el reset inicial y no lleva línea `rst:` propia. Por el texto no
se distingue una relectura del banco del segundo arranque de CR-TB-12, si este repitiera las
mismas marcas del DUT. En los dos casos ocurre antes del primer status en vivo y fuera de la
ventana; el log de actividad del banco ya no conserva esa hora (solo guarda 200 entradas).
