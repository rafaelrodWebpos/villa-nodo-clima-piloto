# TC-TIME-03 — Sin hora tras un corte con SNTP bloqueado

- imagen: `0.0.0-17dc543-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (19:37:38.293 → 19:37:49.597 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- reloj del suscriptor (laptop) frente a pool.ntp.org: -1.04 s

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Precondición: hora válida antes del corte (status con hora_valida = true)
- Bloquear SNTP
- Aviso: desconectar el USB-C de la placa
- Aviso: volver a conectar el USB-C
- Mantener SNTP bloqueado 5 min desde el reenchufe
- Desbloquear SNTP
- log: `TC-TIME-03-serie.log` (243 líneas)
- log: `TC-TIME-03-mqtt.log` (43 líneas)

## Resultado

- hora válida antes del corte: True; SNTP bloqueado: True (rules_ok True); avisos: [True, True]
- corte: placa sin alimentación 22 s; primer status tras el reenchufe: reset=usb, uptime_s=1, hora_valida=False
- con SNTP bloqueado (300 s desde el reenchufe): 5 status (hora_valida ≠ false: 0), 15 medidas (5 de temperatura), con ts no nulo: 0
- tras desbloquear: primera medida con ts a 62.5 s (`{"v":30.7,"u":"°C","ts":1794167144}`, ts − llegada +0.71 s)
- primer status con hora_valida = true tras desbloquear: a +62.6 s
- medidas sin la clave ts: 0; ts enteros con |ts − llegada| > 2 s: []; null después de la primera con ts: 0

**Resultado: FAIL** — AssertionError: el arranque tras el corte no es poweron: {'estado': 'online', 'fw': '0.0.0-17dc543-bench', 'rssi': -39, 'reset': 'usb', 'uptime_s': 1, 'lecturas': 1, 'err_sensor': 0, 'ota': 'ninguno', 'hora_valida': False}
assert 'usb' == 'poweron'
  
  - poweron
  + usb
