# TC-TIME-03 — Sin hora tras un corte con SNTP bloqueado

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (19:42:48.602 → 19:42:59.330 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- reloj del suscriptor (laptop) frente a pool.ntp.org: -1.08 s

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Precondición: hora válida antes del corte (status con hora_valida = true)
- Bloquear SNTP
- Aviso: desconectar el USB-C de la placa
- Aviso: volver a conectar el USB-C
- Mantener SNTP bloqueado 5 min desde el reenchufe
- Desbloquear SNTP
- log: `TC-TIME-03-serie.log` (203 líneas)
- log: `TC-TIME-03-mqtt.log` (43 líneas)

## Resultado

- hora válida antes del corte: True; SNTP bloqueado: True (rules_ok True); avisos: [True, True]
- corte: placa sin alimentación 20 s; primer status tras el reenchufe: reset=poweron, uptime_s=4, hora_valida=False
- con SNTP bloqueado (300 s desde el reenchufe): 6 status (hora_valida ≠ false: 0), 18 medidas (6 de temperatura), con ts no nulo: 0
- tras desbloquear: primera medida con ts a 59.1 s (`{"v":30.9,"u":"°C","ts":1795290650}`, ts − llegada +0.19 s)
- primer status con hora_valida = true tras desbloquear: a +59.1 s
- medidas sin la clave ts: 0; ts enteros con |ts − llegada| > 2 s: []; null después de la primera con ts: 0

**Resultado: PASS** — tras el corte, 18 medidas con ts null y hora_valida false con SNTP bloqueado; al desbloquear, ts a 59.1 s con |ts − llegada| ≤ 2 s y hora_valida true
