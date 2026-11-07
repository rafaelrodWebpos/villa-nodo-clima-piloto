# TC-CON-08 — Corte del broker

- imagen: `0.0.0-5d9228e-bench` (variante bench, run CI 42370306092)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (12:08:15.508 → 12:08:26.141 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Detener el broker hasta «mqtt: intento 10» y su fallo (≈ 4 min)
- Arrancar el broker (el siguiente intento llega a los 60 s)
- log: `TC-CON-08-serie.log` (141 líneas)
- log: `TC-CON-08-mqtt.log` (15 líneas)

## Resultado

- T15: 1; T12: 10; T13: 11 (distancia máx. de T13 a su intento: 10 ms)
- intervalo 1: 1.0 s (esperado 1 s ± 10 %)
- intervalo 2: 2.0 s (esperado 2 s ± 10 %)
- intervalo 3: 4.0 s (esperado 4 s ± 10 %)
- intervalo 4: 8.0 s (esperado 8 s ± 10 %)
- intervalo 5: 16.0 s (esperado 16 s ± 10 %)
- intervalo 6: 32.0 s (esperado 32 s ± 10 %)
- intervalo 7: 60.0 s (esperado 60 s ± 10 %)
- intervalo 8: 60.0 s (esperado 60 s ± 10 %)
- intervalo 9: 60.0 s (esperado 60 s ± 10 %)
- intervalo 10: 60.0 s (esperado 60 s ± 10 %)
- broker de vuelta: T11 no; suscriptor resuscrito a +1.7 s
- primer mensaje del nodo tras el arranque del broker: <base>/status a +59.2 s
- primera medida: +59.2 s (límite 75 s)

**Resultado: FAIL** — AssertionError: sin con: CONECTANDO_BROKER -> OPERATIVO (mqtt_up) en 90 s tras arrancar el broker
assert None
