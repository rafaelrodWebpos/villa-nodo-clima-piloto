# Pendientes del propietario

Tareas que necesitan una decisión o una acción física del propietario. Cada entrada
lleva el contexto y las opciones; cuando se resuelve, se marca con la fecha y lo decidido.

Resueltos: FR-SEN-03 (2026-11-08, TC-SEN-04, H-70); JRN-01.7 con la imagen nueva (2026-11-08, H-69).

## 2026-11-08 · TC-TIME-03 — FR-TIME-03 y FR-MQTT-03 (acción física)

- **Contexto.** H-75. El contrato de FR-TIME-03 (también el de FR-MQTT-03) pide, con SNTP
  bloqueado, cortar y devolver la alimentación del DUT, mantener el bloqueo 5 min y
  desbloquear: antes, medidas con `"ts": null` y `hora_valida` = false; después, en ≤ 30 s
  (más un ciclo), `ts` entero con |ts − llegada| ≤ 2 s. La salida a Internet y el bloqueo
  de SNTP ya los da el fork (por API); falta el corte, que es desenchufar el USB-C.
- **Acción.** Con el test en marcha, un corte a los avisos del banco (como JRN-01.7), unos
  8 minutos en total. El test (TC-TIME-03) está declarado y se escribe cuando se fije la fecha.
- **Estado.** Pendiente.

## 2026-11-08 · NFR-SEN-01 — instrumento de referencia (acción física)

- **Contexto.** Criterio de salida de la Fase 2 sin fila en el plan. Necesita el
  termohigrómetro de referencia junto al sensor (capacidad `reference-instrument`, agenda de
  depuración fila 5, abierta: contraste con los sobres del 33 % y 75 % sin hacer).
- **Acción.** Contrastar la referencia y, después, 30 min de estabilización y 10 lecturas de
  la referencia a ± 30 s de cada publicación.
- **Estado.** Pendiente.
