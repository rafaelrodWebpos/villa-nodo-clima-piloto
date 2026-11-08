# Informe de la mañana — 2026-11-08 (turno de noche, plan H-68)

## En una frase

Todo lo de la lista de esta noche salió **verde**: no hubo ningún rojo ni ningún «no hecho».
La rama `sntp` (cliente SNTP, comandos de banco y watchdog) pasó la regresión completa en el
banco, pero **no está fusionada a main**. Espera a tu auditoría y a JRN-01.7 con la imagen nueva.

## Verde

**En main (firmware de main, sin cambios de firmware esta noche)**

| Test | Qué demuestra | Resultado |
|---|---|---|
| TC-CON-11 (FR-CON-01) | 60 min con el AP del banco apagado: el nodo no se reinicia ni abre el portal | uptime 3648 s, 0 arranques, 7 escaneos sin `clima-*` |
| TC-CON-12 (FR-CON-01) | 60 min con el broker parado: el nodo no se reinicia | uptime 3615 s, 0 arranques |
| TC-MED-02 (FR-MED-02) | Sigue midiendo con el broker parado 10 min | 10 lecturas en 606 s, justo lo esperado |
| TC-MED-01 (FR-MED-01) | Una medida cada 60 s | 10 intervalos entre 59,99 y 60,00 s |

**En la rama `sntp` (imagen `0.0.0-ef118af-bench`, con SNTP, comandos E13 y watchdog de 30 s)**

| Test | Resultado |
|---|---|
| TC-CON-11 y TC-CON-12 (FR-CON-01, 60 + 60 min) | verde, **sin reinicios**: el watchdog no saltó en falso (condición de H-66) |
| JRN-01.0 … JRN-01.5 | verde los 6, con el Home Assistant de prueba (H-52) |
| TC-TIME-05 (FR-TIME-05) | verde: primera medida a 6,1 s del encendido, con `ts: null` |
| TC-TIME-06 (FR-TIME-06) | verde: 20 peticiones SNTP en 5 min, una cada **15,0 s** |
| TC-MED-02 y TC-MED-01 | verde, igual que en main |
| TC-LOG-03 (FR-LOG-03, variante nueva `bench-sin-receptor`, H-67) | verde: con el log UDP hacia una IP sin nadie, 10 ciclos completos y sin reinicio |
| TC-LOG-07 (C-LOG-02, en la CI) | verde: la imagen de producción no lleva `wdt-test` ni `wdt: bloqueando medicion`; la de banco sí |
| TC-TIME-02 y TC-TIME-07 (host) | verde en local (24 de 24 tests de host); la CI de host corre en main al fusionar |

Las tres imágenes de la rama (producción, banco y banco sin receptor) se construyeron en verde en
la CI.

## Rojo

Ninguno.

## No hecho

- **JRN-01.7 con la imagen nueva** y **FR-SEN-03**: necesitan una acción física tuya (ver abajo).
- El xfail estricto de TC-TIME-06 no se ejecutó en el banco sobre main antes del cliente SNTP,
  porque el plan H-68 no lo incluía. La prueba de que main no tenía SNTP es el código: en 491e4fb
  no hay ninguna línea `sntp:`. Queda anotado en la fila del plan (rama `sntp`).

## Para mirar en tu auditoría

- **TC-TIME-06 va justo en el límite.** Los intervalos son de 15,0 s y el contrato pide ≤ 15 s.
  Cumple, pero sin margen. Si prefieres margen, el tick podría bajar, por ejemplo a 14 s; es un
  cambio de una línea en `components/hora/include/hora.h` (`HORA_TICK_MS`). No lo he tocado.
- **El watchdog cambia también la imagen de producción.** `sdkconfig.defaults` pasa a un timeout
  de 30 s con reinicio. Era lo pedido en H-66, pero conviene que lo veas.
- **Revisión de red de la rama.** El hook de push no ve `.env` desde la copia de trabajo de la
  rama, y comprobó 0 patrones. Repetí la revisión a mano con el `.env` de main sobre los 3
  commits de la rama: ningún valor de `.env`, y solo las MAC del DUT.
- **El paso de fuente de C-LOG-02 en `ci.yml`** solo corre al fusionar a main, porque la CI de
  host no se lanza en ramas. En la rama lo ejecuté en local, sin hallazgos.
- **Las filas del plan** de TC-CON-11/12, TC-MED-01/02 y JRN-01.x guardan en main el resultado
  con la imagen de main. El resultado con la imagen de la rama está en
  `testing/regresion-sntp-ef118af.md`, para que la fusión no choque.

## En `testing/pendientes-propietario.md`

1. **FR-SEN-03**: desconectar y reconectar el Dupont de SDA a los avisos del banco (unos 5 min).
2. **JRN-01.7 con la imagen de la rama `sntp`**: un corte manual del USB-C, o 6 si se repiten
   también TC-CFG-02 y TC-MQTT-04. Es la condición, junto con tu auditoría, para fusionar la rama.

## Estado al terminar

- AP y broker del banco **apagados**.
- Home Assistant de prueba **borrado**.
- En el DUT queda la imagen `0.0.0-ef118af-bench-sin-receptor`, de la rama, grabada por
  TC-LOG-03. Antes de JRN-01.7 se graba la que toque.

## Commits de la noche

**main** (CI en verde en todos):

- e231678 — TC-CON-11 y TC-CON-12 (tests)
- f3cbddb — TC-MED-02 (test)
- 1214d19 — pendientes: FR-SEN-03
- 491e4fb — TC-TIME-05 y TC-TIME-06 (tests; TC-TIME-06 en xfail estricto)
- a709198 — CR-TB-14 → issue #50; issue #75 como referencia
- 8fa1951 — TC-MED-01 (test)
- 3ec8885 — pendientes: JRN-01.7 con la imagen nueva
- 2bebc2a — TC-CON-11 y TC-CON-12 en verde
- 563b479 — TC-MED-02 y TC-MED-01 en verde
- (este informe)

**sntp** (sin fusionar; builds de la CI por workflow_dispatch en verde):

- df76a0a — cliente SNTP, validez de la hora y planificador (TC-TIME-02/07 host)
- ef118af — E13, watchdog de 30 s, C-LOG-02 en la CI, variante `bench-sin-receptor` y TC-LOG-03
- 594a166 — regresión de banco en verde sobre ef118af
