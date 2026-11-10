# TC-CON-10 — Pérdida del Wi-Fi en OPERATIVO

- imagen: `0.0.0-17dc543-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (21:48:18.968 → 21:48:30.475 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Apagar el AP 45 s
- Levantar el AP; esperar T11 y la primera medida
- log: `TC-CON-10-serie.log` (108 líneas)
- log: `TC-CON-10-mqtt.log` (15 líneas)

## Resultado

- T16 a +1.3 s de apagar el AP; siguiente «wifi: intento» a 1.0 s (límite 2 s)
- AP de vuelta: T11 sí; primer mensaje del nodo: <base>/status; Last Will de la sesión anterior publicado por el broker: 1
- primera medida: +31.4 s (límite 90 s)

**Resultado: PASS** — T16; siguiente intento a 1.0 s; status primero y medida a 31.4 s del AP
