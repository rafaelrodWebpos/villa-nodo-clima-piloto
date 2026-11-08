# TC-TIME-04 — Resincronización fallida sin perder la hora

- imagen: `0.0.0-17dc543-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (15:53:37.235 → 15:53:47.523 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Esperar la sincronización
- Bloquear SNTP 2 h
- Desbloquear SNTP
- log: `TC-TIME-04-serie.log` (314 líneas)
- log: `TC-TIME-04-mqtt.log` (491 líneas)

## Resultado

- sincronización inicial: `I (9095) nodo: sntp: sincronizado ts=1794153258`
- bloqueo: True (rules_ok True); desbloqueo: True
- en las 2 h: 120 status, 0 con hora_valida ≠ true; 360 medidas, 0 sin ts entero
- «sntp: inicio» 6: ['I (3615765) nodo: sntp: inicio pool.ntp.org', 'I (3625765) nodo: sntp: inicio pool.ntp.org', 'I (3635765) nodo: sntp: inicio pool.ntp.org', 'I (7245815) nodo: sntp: inicio pool.ntp.org']
- «sntp: fallo» 2: ['W (3645775) nodo: sntp: fallo', 'W (7275815) nodo: sntp: fallo']
- sincronizaciones durante el bloqueo: 0; arranques: 0

**Resultado: PASS** — 120 status con hora_valida = true y 360 medidas con ts en 2 h de bloqueo; 2 «sntp: fallo» en la resincronización
