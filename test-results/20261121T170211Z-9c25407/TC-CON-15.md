# TC-CON-15 — Orden de regreso tras un apagón

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (17:02:51.384 → 17:03:01.013 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Apagar AP y broker; reiniciar el nodo (vuelve el primero)
- Levantar el AP a los 180 s; el broker sigue apagado
- Levantar el broker 180 s después del AP
- log: `TC-CON-15-serie.log` (233 líneas)
- log: `TC-CON-15-mqtt.log` (7 líneas)

## Resultado

- arranques tras el reset: 1 (los del reset del banco); después de +15 s: 0
- AP a +193 s; T08 (wifi_up) a +17.4 s del AP (límite 90 s)
- broker a +180 s del AP; primer mensaje del nodo: status {"estado":"online","fw":"0.0.0-9e80669-b
- primera medida a +19.6 s del broker (límite 75 s)

**Resultado: PASS** — sin reinicios; Wi-Fi a 17 s del AP; medida a 20 s del broker
