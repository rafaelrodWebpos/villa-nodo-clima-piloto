# TC-CON-08 — Corte del broker

- imagen: `0.0.0-f18f864-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (09:54:44.471 → 09:54:55.156 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Detener el broker hasta «mqtt: intento 10» y su fallo (≈ 4 min)
- Arrancar el broker (el siguiente intento llega a los 60 s)
- log: `TC-CON-08-serie.log` (193 líneas)
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
- broker de vuelta: T11 sí; suscriptor resuscrito a +2.0 s
- primer mensaje del nodo tras el arranque del broker: <base>/status a +59.4 s
- primera medida: +59.4 s (límite 75 s)

**Resultado: PASS** — 10 intervalos MQTT dentro de ±10 % [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0, 60.0, 60.0]; sin Wi-Fi ni reinicio; status primero y medida a 59.4 s
