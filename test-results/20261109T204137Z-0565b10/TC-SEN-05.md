# TC-SEN-05 — Exactitud frente a la referencia

- imagen: `0.0.0-17dc543-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (20:42:09.697 → 20:42:21.313 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- referencia: sensor interior WH32B de la WS-2000, leído en la consola por el propietario; resolución 0,1 °C y 1 % HR; ± 1 °C declarado de fábrica
- contraste de HR, sobre 33 %: no hecho
- contraste de HR, sobre 75 %: no hecho
- contraste de HR, sal saturada (NaCl, 75 %): 2026-11-09: 75 % HR a 29,7 °C, corrección 0
- contraste de temperatura: no hecho (la temperatura es informativa)

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Aviso: colocar el WH32B junto al SHT41
- Estabilización 30 min
- 10 lecturas de la referencia, una por publicación
- publicación 1: lectura fuera de ± 30 s o sin confirmar (Δt = 45.2 s, confirmado = True); se vuelve a empezar la serie
- log: `TC-SEN-05-mqtt.log` (171 líneas)
- Esperar las 10 lecturas de la referencia en TC-SEN-05-referencia.txt

## Resultado

| # | Δt lectura (s) | T nodo | T ref | ΔT | HR nodo | HR ref | ΔHR |
|---|---|---|---|---|---|---|---|
| 1 | +12.9 | 30.5 | 30.0 | +0.5 | 74.9 | 74.0 | +0.9 |
| 2 | +6.3 | 30.5 | 30.0 | +0.5 | 74.6 | 74.0 | +0.6 |
| 3 | +14.4 | 30.5 | 30.1 | +0.4 | 75.1 | 74.0 | +1.1 |
| 4 | +6.1 | 30.5 | 30.1 | +0.4 | 74.8 | 74.0 | +0.8 |
| 5 | +6.5 | 30.5 | 30.1 | +0.4 | 75.0 | 74.0 | +1.0 |
| 6 | +5.6 | 30.5 | 30.1 | +0.4 | 75.1 | 74.0 | +1.1 |
| 7 | +8.0 | 30.5 | 30.1 | +0.4 | 75.3 | 74.0 | +1.3 |
| 8 | +10.7 | 30.5 | 30.2 | +0.3 | 76.0 | 74.0 | +2.0 |
| 9 | +5.8 | 30.4 | 30.2 | +0.2 | 75.6 | 74.0 | +1.6 |
| 10 | +6.8 | 30.4 | 30.2 | +0.2 | 75.5 | 74.0 | +1.5 |

- diferencia media de HR: +1.19 % (tolerancia ± 3.0)
- diferencia media de temperatura: +0.37 °C (informativa: referencia sin contrastar en temperatura)
- máximas: |ΔT| = 0.50 °C, |ΔHR| = 2.00 %

**Resultado: PASS** — ΔHR medio +1.19 % (± 3.0) en 10 parejas; ΔT medio +0.37 °C (informativo)
