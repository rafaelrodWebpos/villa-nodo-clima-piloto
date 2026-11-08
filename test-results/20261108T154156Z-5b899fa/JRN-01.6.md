# JRN-01.6 — Hora por SNTP y medidas con ts

- imagen: `0.0.0-17dc543-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (15:42:35.423 → 15:42:46.767 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- reloj del suscriptor (laptop) frente a pool.ntp.org: -0.82 s

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Esperar dos ciclos de medida (≈ 130 s)
- log: `JRN-01.6-serie.log` (189 líneas)
- log: `JRN-01.6-mqtt.log` (15 líneas)

## Resultado

- salida del AP: True (rules_ok True)
- wifi_up: `I (5225) nodo: con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)`
- sincronización: `I (9295) nodo: sntp: sincronizado ts=1794152597` → 4.07 s desde wifi_up (≤ 30 s)
- primer status posterior: uptime_s=60, hora_valida=True
- temperatura: 3 en vivo; primera `{"v":31.2,"u":"°C","ts":null}`
- humedad: 3 en vivo; primera `{"v":68.9,"u":"%","ts":null}`
- punto_rocio: 3 en vivo; primera `{"v":24.8,"u":"°C","ts":null}`
- intervalos entre medidas de temperatura (sin la de T11): [60.0] s
- ts − llegada en las 6 medidas con ts: [0.14, 0.01, 0.01, 0.14, 0.09, 0.09]

**Resultado: PASS** — sincroniza a 4.07 s de wifi_up; hora_valida true; medidas con |ts − llegada| ≤ 0.14 s; intervalo [60.0] s
