# TC-WDT-01 — análisis del rojo (24 h sobre 0.0.0-17dc543-bench, fork villa-1)

Resultado registrado: **FAIL** en `assert not boots` (`tests/bench/test_wdt.py:158`). Las demás
aserciones que se evaluaron antes de ese assert, y las que quedaron detrás, se comprueban aquí con los
valores de `TC-WDT-01.md` y `TC-WDT-01-serie.log`; no se marca verde: lo decide el propietario.

## Las 3 líneas «boot:» son una relectura del banco, no un reinicio

- `TC-WDT-01-serie.log` líneas 46–112 (67 líneas, del `I (368) boot: Loaded app…` al
  `I (4115) … (backoff)`) aparecen **idénticas** otra vez en las líneas 113–179; tras la copia sigue
  `I (4125) wifi:state: init -> auth`, la continuación natural de la línea 112.
- `Registro.leer` (`tests/bench/benchlib.py:351`) descarta duplicados por (ts del banco, texto):
  el banco volvió a entregar ese bloque con otra marca de tiempo, dentro de la ventana
  (t_ini − 60 s), y el test lo contó. Las 3 líneas del assert (`I (368) boot:`, `I (369) boot:`,
  `I (485) nodo: boot: … reset=usb`) son las de la copia (líneas 113, 114 y 139).
- Quitando la copia: **un solo arranque** (`rst:0x15`, línea 15), el previsto al resetear tras el
  aprovisionamiento, antes de la ventana; el reloj de esp_log sube sin ningún retroceso desde
  `I (27)` hasta `I (86460615)`.

## Contrato de NFR-WDT-01 (bench) y 22.1-2 con los valores registrados

| Aserción | Valor | Veredicto |
|---|---|---|
| task_wdt | 0 líneas | PASS |
| boot:/rst: en la ventana | 3, todas de la copia releída; 0 tras quitarla | PASS tras deduplicar |
| uptime_s creciente | ninguno no creciente en 1422 status; 4 → 86460 (= 86456 s de reloj) | PASS |
| reset sin cambio | ['usb'] | PASS |
| 5 cortes hechos | broker 7203 s, wifi 21612 s, broker 36022 s, wifi 50429 s, broker 64808 s | PASS |
| recuperación ≤ 150 s | 3,4 / 26,1 / 3,5 / 26,0 / 3,3 s | PASS |
| Δlecturas = ciclos ± 2 | 1441 en 86456 s = 1441 ciclos (1440 ± 2 en 24 h) | PASS |
| publicaciones por medida = ciclos en OPERATIVO ± 2 | 1421 / 1421 / 1421 con 1421 ciclos en OPERATIVO (20 sin OPERATIVO: los dos cortes de Wi-Fi) | PASS |
| control de consola | 1440 med: en la ventana; ningún tramo de 10 min con < 5 | PASS |
| Δerr_sensor | 0 | — |
