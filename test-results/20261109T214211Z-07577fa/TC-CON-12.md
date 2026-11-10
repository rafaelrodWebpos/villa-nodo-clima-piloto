# TC-CON-12 — Broker parado 60 min

- imagen: `0.0.0-17dc543-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (23:20:15.701 → 23:20:26.713 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Corte de 60 min: broker parado (Wi-Fi arriba)
- Fin del corte: devolver el broker; esperar el primer status
- Escaneo con el AP del banco apagado un momento (CR-TB-14, como H-63)
- log: `TC-CON-12-serie.log` (1226 líneas)
- log: `TC-CON-12-mqtt.log` (23 líneas)

## Resultado

- antes del corte: reset=usb, uptime_s=4
- primer status tras la vuelta: a +4.8 s, reset=usb, uptime_s=3615
- líneas boot:/rst: en la ventana: 0
- control de la consola: 60 líneas med: durante el corte; tramos de 10 min con < 5: ninguno
- escaneo a t=3728 s: ningún clima-*

**Resultado: PASS** — corte de 60 min sin reinicio: uptime_s=3615, reset=usb, 0 boot:, 1 escaneos sin clima-*
