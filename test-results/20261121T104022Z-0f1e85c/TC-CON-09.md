# TC-CON-09 — Pérdida del Wi-Fi esperando al broker

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (11:11:12.424 → 11:11:22.372 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Reset con el AP y el broker apagados; esperar «wifi: intento 5»
- Levantar el AP (broker apagado); esperar T08 y dos intentos MQTT
- Apagar el AP; esperar T14 y observar 60 s
- log: `TC-CON-09-serie.log` (102 líneas)
- log: `TC-CON-09-mqtt.log` (0 líneas)

## Resultado

- intentos de unión antes de T08: 6; espacios entre intentos: [3.4, 2.4, 8.4, 10.4, 18.4] s
- T14 a +5.1 s de apagar el AP; siguiente «wifi: intento» a 1.0 s de T14 (límite 2 s)
- intentos MQTT tras T14 en 60 s: 0

**Resultado: PASS** — T14; siguiente intento de unión a 1.0 s; sin intentos MQTT ni reinicio
