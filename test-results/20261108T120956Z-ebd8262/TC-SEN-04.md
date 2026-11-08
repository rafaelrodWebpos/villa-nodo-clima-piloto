# TC-SEN-04 — Recuperación tras desconectar SDA

- imagen: `0.0.0-3f2eac8-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.5` (12:10:23.344 → 12:10:38.625 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Precondición: dos status en vivo con medidas válidas
- Aviso: desconectar SDA
- Esperar 3 ciclos con lectura inválida (status con err_sensor creciente)
- Aviso: reconectar SDA
- Esperar las medidas del primer ciclo tras reconectar y un status más
- log: `TC-SEN-04-serie.log` (157 líneas)
- log: `TC-SEN-04-mqtt.log` (18 líneas)

## Resultado

- operador: desconexión confirmada a 24.3 s del aviso; reconexión a 29.7 s del aviso; SDA suelto ≈ 152 s
- último status antes: uptime_s=60, lecturas=2, err_sensor=0, reset=usb
- status con SDA suelto: 3; err_sensor [1, 2, 3] (Δ = 3)
- medidas en vivo con SDA suelto: 0
- líneas «med: invalida» en la consola: 3 (W (120555) nodo: med: invalida (nack) …)
- primeras medidas tras reconectar: temperatura={"v":30.3,"u":"°C","ts":null} a +30.3 s, humedad={"v":69.5,"u":"%","ts":null} a +30.3 s, punto_rocio={"v":24.1,"u":"°C","ts":null} a +30.3 s
- status tras reconectar: uptime_s=300, lecturas=3, err_sensor=3, reset=usb
- arranques en la consola: 1

**Resultado: PASS** — 0 medidas con SDA suelto, Δerr_sensor=3, tres medidas válidas a 30.3 s de reconectar (≤ 61 s); sin reinicio
