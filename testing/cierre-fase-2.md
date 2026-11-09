# Cierre de la Fase 2 — Telemetría: MQTT y Home Assistant

- **Decisión:** H-79 (propietario, 2026-11-09). La Fase 2 se cierra con todas las pruebas
  ejecutables en verde. Las que dependen de capacidades del banco que hoy están en `no`
  quedan **bloqueadas por el banco, no fallidas**. Ampliar el fork del banco con esas
  capacidades será una sesión aparte. La Fase 3 no se empieza.
- **FSD:** 0.9.7 (§3.2, criterios de salida). §3.2 dice que la fase no puede salir mientras
  una capacidad derivada siga en `no` [user]. H-79 la cierra como excepción del propietario,
  con los bloqueados de abajo.
- **Imagen de referencia:** `0.0.0-17dc543-bench` (run 42495454952). El firmware (main/,
  components/, sdkconfig.defaults) no cambia de 7fb10da a 17dc543, ni hasta este cierre.
- **Banco:** fork `rafaelrodWebpos/Embedded-AI-Harness`, tag villa-1, con salida a Internet del
  AP y bloqueo de SNTP (CR-TB-01/02, `testing/regresion-fork-villa-1.md`).

## Bloqueados por capacidades del banco

| Requisito / fila | Capacidad en `no` | Petición | Estado del test |
|---|---|---|---|
| FR-TIME-02, fila bench⁺ | `bench-serial-write` | — (existe `POST /api/serial/write`, pero el banco no la reporta) | TC-TIME-08 declarado, sin implementar |
| NFR-WDT-01, fila target | `bench-serial-write` | — | sin fila declarada |
| FR-MQTT-07 | `bench-mqtt-auth` | CR-TB-03 | sin fila declarada |
| FR-LOG-01 | `bench-traffic-capture` | CR-TB-04 | TC-LOG-04 declarado, sin implementar |
| FR-LOG-02, fila de captura | `bench-traffic-capture` | CR-TB-04 | sin fila declarada |

## Requisitos de §3.2 con su estado y evidencia

Formato de cada celda de tests: test (nivel, estado, commit; evidencia o run de CI). Los tests
de nivel host y «other» corren en cada commit de la CI y están en verde en el de este cierre.

| Requisito | Estado | Tests |
|---|---|---|
| FR-MQTT-01 | verde | JRN-01.6 (bench+, successful, 5b899fa; test-results/20261108T154156Z-5b899fa/JRN-01.6.md) |
| FR-MQTT-02 | verde | TC-MQTT-01 (host, successful, 56e2b85; CI 42327311133) |
| FR-MQTT-03 | verde | JRN-01.6 (bench+, successful, 5b899fa; test-results/20261108T154156Z-5b899fa/JRN-01.6.md)<br>TC-TIME-03 (bench+, successful, c32b832; test-results/20261108T193705Z-ab384dd/TC-TIME-03-reevaluacion.md) |
| FR-MQTT-04 | verde | TC-MQTT-03 (bench, successful, 5d9228e; test-results/20261107T115935Z-5d9228e/) |
| FR-MQTT-05 | verde | TC-MQTT-04 (bench, successful, 3f2eac8; test-results/20261108T111528Z-3f2eac8/TC-MQTT-04.md) |
| FR-MQTT-06 | verde | JRN-01.4 (bench, successful, 7096cb7; test-results/20261107T141937Z-7096cb7/)<br>TC-CON-08 (bench, successful, 581ec56; test-results/20261107T124105Z-581ec56/)<br>TC-CON-10 (bench, successful, 5d9228e; test-results/20261107T115935Z-5d9228e/) |
| FR-MQTT-07 | **bloqueado** — `bench-mqtt-auth` (CR-TB-03); sin fila de test declarada | — |
| FR-MQTT-08 | verde | JRN-01.4 (bench, successful, 7096cb7; test-results/20261107T141937Z-7096cb7/)<br>TC-DIAG-01 (host, successful, ce15ce2; CI host tests + secret scan de ce15ce2 (verde); en la placa, «reset=usb» tras /api/serial/reset (test-results/*-b510420-reset-en/))<br>TC-MQTT-02 (host, successful, 56e2b85; CI 42327311133) |
| FR-HA-01 | verde | JRN-01.5 (bench, successful, 7096cb7; test-results/20261107T141937Z-7096cb7/)<br>TC-MQTT-03 (bench, successful, 5d9228e; test-results/20261107T115935Z-5d9228e/) |
| FR-HA-02 | verde | TC-HA-01 (host, successful, 9ddfcb4; CI 42368833137) |
| FR-HA-03 | verde | TC-HA-01 (host, successful, 9ddfcb4; CI 42368833137) |
| FR-MED-01 | verde | JRN-01.6 (bench+, successful, 5b899fa; test-results/20261108T154156Z-5b899fa/JRN-01.6.md)<br>TC-MED-01 (bench, successful, 2bebc2a; test-results/20261107T234415Z-2bebc2a/TC-MED-01.md) |
| FR-MED-02 | verde | TC-MED-02 (bench, successful, 2bebc2a; test-results/20261107T234415Z-2bebc2a/TC-MED-02.md) |
| FR-MED-06 | verde | TC-MED-06 (bench+, successful, 5b899fa; test-results/20261108T154156Z-5b899fa/TC-MED-06.md) |
| FR-SEN-03 | verde | TC-SEN-04 (bench, successful, ebd8262; test-results/20261108T120956Z-ebd8262/TC-SEN-04.md) |
| NFR-SEN-01 | verde | TC-SEN-05 (bench, successful, 0565b10; test-results/20261109T204137Z-0565b10/TC-SEN-05.md) |
| FR-CON-01 | verde | TC-CON-11 (bench, successful, e231678; test-results/20261107T213350Z-e231678/TC-CON-11.md)<br>TC-CON-12 (bench, successful, e231678; test-results/20261107T213350Z-e231678/TC-CON-12.md) |
| FR-CON-02 | verde | TC-CON-02 (host, successful, 07da69b; CI 42138329897)<br>TC-CON-03 (bench, successful, 5f20820; test-results/20261106T005824Z-5f20820/TC-CON-03.md)<br>TC-CON-08 (bench, successful, 581ec56; test-results/20261107T124105Z-581ec56/) |
| FR-CON-03 | verde | TC-CON-10 (bench, successful, 5d9228e; test-results/20261107T115935Z-5d9228e/) |
| FR-CON-04 | verde | TC-CON-08 (bench, successful, 581ec56; test-results/20261107T124105Z-581ec56/) |
| FR-CON-05 | verde | JRN-01.7 (bench, successful, 3f2eac8; test-results/20261108T111528Z-3f2eac8/JRN-01.7.md) |
| FR-CON-06 | verde | TC-CON-06 (bench, successful, c9838dc; test-results/20261106T020031Z-c9838dc/TC-CON-06.md) |
| FR-CFG-01 | verde | JRN-01.7 (bench, successful, 3f2eac8; test-results/20261108T111528Z-3f2eac8/JRN-01.7.md)<br>TC-CFG-02 (bench, successful, 3f2eac8; test-results/20261108T111528Z-3f2eac8/TC-CFG-02.md) |
| FR-TIME-01 | verde | JRN-01.6 (bench+, successful, 5b899fa; test-results/20261108T154156Z-5b899fa/JRN-01.6.md) |
| FR-TIME-02 | host en verde; fila bench⁺ (TC-TIME-08) **bloqueada** — `bench-serial-write` | TC-TIME-02 (host, successful, ed91e26; CI 42476259789)<br>TC-TIME-08 (bench+, declarado, —) |
| FR-TIME-03 | verde | TC-TIME-03 (bench+, successful, c32b832; test-results/20261108T193705Z-ab384dd/TC-TIME-03-reevaluacion.md) |
| FR-TIME-04 | verde | TC-TIME-07 (host, successful, ed91e26; CI 42476259789)<br>TC-TIME-04 (bench+, successful, 5b899fa; test-results/20261108T155258Z-5b899fa/TC-TIME-04.md) |
| FR-TIME-05 | verde | TC-TIME-05 (bench, successful, ef118af; test-results/20261108T000941Z-ef118af/TC-TIME-05.md) |
| FR-TIME-06 | verde | TC-TIME-07 (host, successful, ed91e26; CI 42476259789)<br>TC-TIME-06 (bench, successful, 7fb10da; test-results/20261108T123657Z-7fb10da/TC-TIME-06.md) |
| NFR-WDT-01 | fila bench en verde; fila target **bloqueada** — `bench-serial-write` (comando wdt-test de E13); sin fila declarada | TC-WDT-01 (bench, successful, d212ffa; test-results/20261108T195622Z-050dd09/TC-WDT-01-reevaluacion.md) |
| FR-SEC-03 | verde | TC-SEC-02 (host, successful, 9c382b9; CI 41951228893) |
| FR-LOG-01 | **bloqueado** — `bench-traffic-capture` (CR-TB-04); TC-LOG-04 declarado | TC-LOG-04 (bench, declarado, —) |
| FR-LOG-02 | verde (Fase 1 y host); fila de captura **bloqueada** — `bench-traffic-capture` (CR-TB-04); sin fila declarada | JRN-01.3 (bench, successful, 7096cb7; test-results/20261107T141937Z-7096cb7/)<br>TC-LOG-02 (host, successful, 0d3da79; CI 42110797953)<br>TC-LOG-05 (host, successful, c9205dd; CI 42376460822)<br>TC-LOG-06 (host, successful, 7096cb7; CI 42377699449) |
| FR-LOG-03 | verde | TC-LOG-05 (host, successful, c9205dd; CI 42376460822)<br>TC-LOG-06 (host, successful, 7096cb7; CI 42377699449)<br>TC-LOG-03 (bench, successful, ef118af; test-results/20261108T025600Z-ef118af/TC-LOG-03.md) |
| C-LOG-02 | verde | TC-LOG-07 (other, successful, ef118af; CI 42417733022) |
| T08 | verde | JRN-01.3 (bench, successful, 7096cb7; test-results/20261107T141937Z-7096cb7/)<br>TC-CON-01 (host, successful, 56e2b85; CI 42327311133) |
| T11 | verde | JRN-01.4 (bench, successful, 7096cb7; test-results/20261107T141937Z-7096cb7/)<br>TC-CON-01 (host, successful, 56e2b85; CI 42327311133) |
| T12 | verde | TC-CON-01 (host, successful, 56e2b85; CI 42327311133)<br>TC-CON-08 (bench, successful, 581ec56; test-results/20261107T124105Z-581ec56/) |
| T13 | verde | TC-CON-01 (host, successful, 56e2b85; CI 42327311133)<br>TC-CON-08 (bench, successful, 581ec56; test-results/20261107T124105Z-581ec56/) |
| T14 | verde | TC-CON-01 (host, successful, 56e2b85; CI 42327311133)<br>TC-CON-09 (bench, successful, 5d9228e; test-results/20261107T115935Z-5d9228e/) |
| T15 | verde | TC-CON-01 (host, successful, 56e2b85; CI 42327311133)<br>TC-CON-08 (bench, successful, 581ec56; test-results/20261107T124105Z-581ec56/) |
| T16 | verde | TC-CON-01 (host, successful, 56e2b85; CI 42327311133)<br>TC-CON-10 (bench, successful, 5d9228e; test-results/20261107T115935Z-5d9228e/) |

## Salvedades

- **Imagen de la evidencia.** Corrieron sobre el firmware final (7fb10da = 17dc543):
  TC-TIME-06, JRN-01.0…01.5 y TC-CON-08 (regresión del fork sobre 47a52ea), JRN-01.6,
  TC-MED-06, TC-TIME-04, TC-TIME-03, TC-WDT-01 y TC-SEN-05. Los demás tienen su último verde
  sobre un firmware anterior:
  - sobre ef118af o la imagen de 3f2eac8, que solo difieren en el tick SNTP (15 s → 10 s,
    H-71): TC-LOG-03, TC-TIME-05, JRN-01.7, TC-CFG-02, TC-MQTT-04 y TC-SEN-04;
  - sobre 5d9228e, e231678 y 2bebc2a, anteriores al cliente SNTP (df76a0a) y al watchdog
    (ef118af): TC-CON-09, TC-CON-10, TC-MQTT-03, TC-CON-11, TC-CON-12, TC-MED-01 y
    TC-MED-02. Los cortes de broker y de Wi-Fi con recuperación se volvieron a ver sobre el
    firmware final en TC-WDT-01 (5 cortes) y en TC-CON-08 (regresión del fork).
- **Reevaluaciones.** TC-TIME-03 (H-76) y TC-WDT-01 (H-78) están en verde por reevaluación de
  su evidencia con una comprobación corregida; el rojo original queda en el historial.
- **NFR-SEN-01.** La temperatura es informativa (FSD 0.9.7): el WH32B solo está contrastado en
  HR (sal saturada, 75 %).
- **Observaciones del banco abiertas:** CR-TB-12 (doble arranque tras un reset; bloque de
  arranque repetido en TC-WDT-01), CR-TB-10, -11, -13, -14 y -15.
