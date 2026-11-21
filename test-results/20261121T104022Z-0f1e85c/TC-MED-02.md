# TC-MED-02 — Medición con el broker parado 10 min

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (11:34:56.270 → 11:35:06.415 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Esperar dos status en vivo (al conectar y en el ciclo siguiente)
- Parar el broker 10 min
- Arrancar el broker; esperar el primer status en vivo
- log: `TC-MED-02-serie.log` (338 líneas)
- log: `TC-MED-02-mqtt.log` (19 líneas)

## Resultado

- último status antes del corte: uptime_s=60, lecturas=2, reset=usb
- primer status tras el broker: a +3.4 s, uptime_s=665, lecturas=12, reset=usb
- Δuptime_s=605 → ⌊Δ/60⌋=10; Δlecturas=10 (tolerancia ± 1)

**Resultado: PASS** — Δlecturas=10 con Δuptime_s=605 (⌊Δ/60⌋=10); sin reinicio
