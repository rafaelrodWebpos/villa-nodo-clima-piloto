# JRN-01.6 — Hora por SNTP y medidas con ts

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (10:12:35.727 → 10:12:47.220 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- reloj del suscriptor (laptop) frente a pool.ntp.org: -0.51 s

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Esperar dos ciclos de medida (≈ 130 s)
- log: `JRN-01.6-serie.log` (126 líneas)
- log: `JRN-01.6-mqtt.log` (15 líneas)

## Resultado

- salida del AP: True (rules_ok True)
- wifi_up: `I (15953) nodo: con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)`
- sincronización: `I (21313) nodo: sntp: sincronizado ts=1795256001` → 5.36 s desde wifi_up (≤ 30 s)
- primer status posterior: uptime_s=60, hora_valida=True
- temperatura: 3 en vivo; primera `{"v":29.8,"u":"°C","ts":null}`
- humedad: 3 en vivo; primera `{"v":61.7,"u":"%","ts":null}`
- punto_rocio: 3 en vivo; primera `{"v":21.6,"u":"°C","ts":null}`
- intervalos entre medidas de temperatura (sin la de T11): [60.0] s
- ts − llegada en las 6 medidas con ts: [0.14, 0.1, 0.09, 0.15, 0.1, 0.09]

**Resultado: PASS** — sincroniza a 5.36 s de wifi_up; hora_valida true; medidas con |ts − llegada| ≤ 0.15 s; intervalo [60.0] s
