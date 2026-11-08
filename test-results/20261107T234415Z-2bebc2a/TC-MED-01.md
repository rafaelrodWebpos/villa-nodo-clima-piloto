# TC-MED-01 — Periodo de medición de 60 s

- imagen: `0.0.0-2bebc2a-bench` (variante bench, run CI 42426367149)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (23:57:11.826 → 23:57:23.739 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Capturar 11 mensajes de temperatura en vivo
- log: `TC-MED-01-serie.log` (183 líneas)
- log: `TC-MED-01-mqtt.log` (51 líneas)

## Resultado

- mensajes de temperatura en vivo: 12; de la última sesión, sin el de T11: 11
- intervalos (s): [60.0, 59.99, 60.0, 60.0, 60.0, 60.0, 60.0, 60.0, 60.0, 60.0]
- deriva acumulada en 10 ciclos: -0.01 s

**Resultado: PASS** — 10 intervalos en [59.99, 60.0] s; deriva -0.01 s
