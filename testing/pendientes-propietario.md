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
- **Estado.** Preparado (H-77, 2026-11-09): referencia WH32B de la WS-2000, contrastada solo al
  75 % con la prueba de la sal; test TC-SEN-05 escrito, sin lanzar. FSD 0.9.7 (H-77): la prueba de
  la sal basta para la HR; la temperatura es informativa. Hecho el 2026-11-09: TC-SEN-05 en verde
  (ΔHR medio +1,19 %HR; ΔT medio +0,37 °C informativo).

## 2026-11-14 · bench-serial-write no llega al lector de comandos E13 (bloquea TC-TIME-08 y TC-WDT-02)

- **Contexto.** El banco solo expone el puerto `/dev/ttyACM0` del slot, que es el USB-Serial/JTAG del DUT.
  El lector de comandos E13 lee de UART0 (el CH343), como dice el FSD (§18). Lo que escribe
  `POST /api/serial/write` nunca llega al lector: en TC-TIME-08, «reiniciar» no produjo ninguna línea `boot:`.
- **Opciones.**
  - (a) FSD: que E13 también lea del USB-Serial/JTAG en la imagen de banco. Exige el driver de USJ,
    que H-58 dejó sin aplicar por el riesgo de bloqueos.
  - (b) Banco: asignar el puerto del CH343 (VID:PID `1a86:55d3`) a un slot y escribir ahí. Es configuración
    de la Pi, a decidir por el propietario.
- **Estado.** Resuelto (2026-11-14): opción (a). TC-TIME-08 y TC-WDT-02 en verde; el texto del FSD está en `fsd_pending` (E13-USJ).

## 2026-11-15 · Auditoría de cierre de la Fase 3 (H-91): pendientes antes de la instalación (S2)

- **Contexto.** El informe de H-91 está fuera del repositorio. Veredicto: sin puerta trasera, S1 sí y S3 sí con
  condiciones. A3-01, A3-04 y A3-05 quedan corregidos en el firmware y en la CI.
- **Pendientes antes de la instalación (puerta S2), por decisión del propietario:**
  - A3-02 (baja, `ota_politica.c`): un salto que volvía a github.com no se revisaba contra la ruta del repo ni contra
    ota-test-*. **Corregido el 2026-11-18** (TC-OTA-02 ampliado).
  - A3-03 (baja, robustez, `ota_descarga.c`): estado compartido entre una tarea abortada y una descarga nueva.
    **Corregido el 2026-11-18** (contexto propio de cada tarea y turno `ota_turno`; TC-OTA-16).
- **Estado.** Abiertos. No bloquean el tag v0.0.1; sí bloquean la instalación en la villa (S2). Van en el paquete
  pendiente antes de S2 con ESP-IDF 6.0.3 y #52 (`testing/plan-fase-3.md`, aprobado el 2026-11-15).
