# TC-SEN-04 — Recuperación tras desconectar SDA

- imagen: `0.0.0-fad73ef-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (15:26:44.878 → 15:26:55.456 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Precondición: dos status en vivo con medidas válidas
- Aviso: desconectar SDA
- Esperar 3 ciclos con lectura inválida (status con err_sensor creciente)
- Aviso: reconectar SDA
- Esperar las medidas del primer ciclo tras reconectar y un status más
- log: `TC-SEN-04-serie.log` (212 líneas)
- log: `TC-SEN-04-mqtt.log` (18 líneas)

## Resultado

- operador: desconexión confirmada a 56.3 s del aviso; reconexión a 26.3 s del aviso; SDA suelto ≈ 120 s
- último status antes: uptime_s=60, lecturas=2, err_sensor=0, reset=usb
- status con SDA suelto: 2; err_sensor [2, 3] (Δ = 3)
- medidas en vivo con SDA suelto: 0
- líneas «med: invalida» en la consola: 3 (W (120553) nodo: med: invalida (nack) …)
- primeras medidas tras reconectar: temperatura={"v":31.0,"u":"°C","ts":null} a +33.6 s, humedad={"v":76.1,"u":"%","ts":null} a +33.7 s, punto_rocio={"v":26.3,"u":"°C","ts":null} a +33.7 s
- status tras reconectar: uptime_s=300, lecturas=3, err_sensor=3, reset=usb
- arranques en la consola: 1

**Resultado: PASS** — 0 medidas con SDA suelto, Δerr_sensor=3, tres medidas válidas a 33.7 s de reconectar (≤ 61 s); sin reinicio
