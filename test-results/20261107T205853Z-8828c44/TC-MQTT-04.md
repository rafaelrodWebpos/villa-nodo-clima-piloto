# TC-MQTT-04 — Last Will tras un corte de alimentación

- corte = última muestra del slot presente antes de verlo ausente (cota por arriba del retraso)

## Resultado

- JRN-01.7 corte 1: Last Will 74.0 s; retenido: sí
- TC-CFG-02 corte 1: Last Will 65.2 s; retenido: sí
- TC-CFG-02 corte 2: Last Will 83.5 s; retenido: sí
- TC-CFG-02 corte 3: Last Will 81.1 s; retenido: sí
- TC-CFG-02 corte 4: Last Will 70.3 s; retenido: sí
- TC-CFG-02 corte 5: Last Will 79.9 s; retenido: sí

**Resultado: PASS** — 6 cortes: Last Will retenido en ≤ 83.5 s (límite 100 s)
