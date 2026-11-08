# Regresión de banco de la rama sntp (ef118af) — turno de noche H-68

Imagen: `0.0.0-ef118af-bench` (cliente SNTP, comandos E13 y watchdog de 30 s), CI run
42417735201 (workflow_dispatch, ref sntp). Condición de H-66: con el watchdog, FR-CON-01 y
JRN-01.0–01.5 sin reinicios. La rama no se fusiona a main hasta la auditoría del propietario y
JRN-01.7 en verde con esta imagen (H-68).

| Test | Resultado | Evidencia |
|---|---|---|
| TC-CON-11 (FR-CON-01, AP apagado 60 min) | PASS — uptime_s 3648, 0 boot:, 7 escaneos sin clima-* | test-results/20261108T000941Z-ef118af/TC-CON-11.md |
| TC-CON-12 (FR-CON-01, broker parado 60 min) | PASS — uptime_s 3615, 0 boot: | test-results/20261108T000941Z-ef118af/TC-CON-12.md |
| JRN-01.0 … JRN-01.5 | PASS los 6 (Home Assistant de prueba en la laptop, H-52) | test-results/20261108T000941Z-ef118af/JRN-01.*.md |
| TC-TIME-05 (FR-TIME-05) | PASS — medida a 6,1 s del encendido, ts null | test-results/20261108T000941Z-ef118af/TC-TIME-05.md |
| TC-TIME-06 (FR-TIME-06) | PASS — 20 peticiones, intervalos de 15,0 s | test-results/20261108T000941Z-ef118af/TC-TIME-06.md |
| TC-MED-02 (FR-MED-02) | PASS — Δlecturas 10 con Δuptime_s 606 | test-results/20261108T000941Z-ef118af/TC-MED-02.md |
| TC-MED-01 (FR-MED-01) | PASS — intervalos 59,99–60,01 s | test-results/20261108T000941Z-ef118af/TC-MED-01.md |
| TC-LOG-03 (FR-LOG-03, variante bench-sin-receptor, run 42417737075) | PASS — 10 ciclos, sin reinicio | test-results/20261108T025600Z-ef118af/TC-LOG-03.md |

Las filas del plan de TC-CON-11/12, TC-MED-01/02 y JRN-01.0–01.5 guardan en main el resultado
con la imagen de main; este fichero guarda el de la rama para no chocar al fusionar.
No ejecutado: JRN-01.7 (corte manual, testing/pendientes-propietario.md).
