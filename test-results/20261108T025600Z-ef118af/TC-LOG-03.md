# TC-LOG-03 — Log UDP hacia una IP sin receptor

- imagen: `0.0.0-ef118af-bench-sin-receptor` (variante bench-sin-receptor, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (02:56:39.189 → 02:56:49.603 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- variante bench-sin-receptor: log UDP hacia una IP sin uso de la red del AP del banco

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Observar 10 ciclos de medición
- log: `TC-LOG-03-serie.log` (263 líneas)
- log: `TC-LOG-03-mqtt.log` (51 líneas)

## Resultado

- status en vivo: 12; ciclos observados: 10
- ciclos sin las 3 medidas: ninguno
- intervalos entre temperaturas (s): [60.0, 60.0, 60.0, 60.0, 59.99, 60.0, 60.0, 60.0, 60.0]
- uptime_s: [4, 60, 120, 180, 240, 300, 360, 420, 480, 540, 600, 660]

**Resultado: PASS** — 10 ciclos con 3 medidas y status; intervalos en [59.99, 60.0] s; sin reinicio
