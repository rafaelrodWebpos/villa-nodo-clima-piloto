# TC-CON-11 — AP apagado 60 min

- imagen: `0.0.0-e231678-bench` (variante bench, run CI 42416208572)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (21:34:28.751 → 21:34:39.902 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Corte de 60 min: AP del banco apagado
- Fin del corte: devolver el AP; esperar el primer status
- log: `TC-CON-11-serie.log` (448 líneas)
- log: `TC-CON-11-mqtt.log` (23 líneas)

## Resultado

- antes del corte: reset=usb, uptime_s=4
- primer status tras la vuelta: a +32.8 s, reset=usb, uptime_s=3648
- líneas boot:/rst: en la ventana: 0
- control de la consola: 60 líneas med: durante el corte; tramos de 10 min con < 5: ninguno
- escaneo a t=65 s: ningún clima-*
- escaneo a t=670 s: ningún clima-*
- escaneo a t=1275 s: ningún clima-*
- escaneo a t=1879 s: ningún clima-*
- escaneo a t=2484 s: ningún clima-*
- escaneo a t=3089 s: ningún clima-*
- escaneo a t=3605 s: ningún clima-*

**Resultado: PASS** — corte de 60 min sin reinicio: uptime_s=3648, reset=usb, 0 boot:, 7 escaneos sin clima-*
