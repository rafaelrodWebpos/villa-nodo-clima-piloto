# FORK-02 — Salida a Internet real y bloqueo de SNTP

- imagen: `0.0.0-47a52ea-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (14:17:13.475 → 14:17:25.399 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Encender la salida a Internet del AP
- Esperar un status y una medida con hora
- Bloquear SNTP y reiniciar el DUT
- Desbloquear SNTP
- log: `FORK-02-serie.log` (393 líneas)
- log: `FORK-02-mqtt.log` (31 líneas)

## Resultado

- salida encendida: internet=True sntp_blocked=False lan_blocked=True rules_ok=True reglas=15
- sincronización: `I (18885) nodo: sntp: sincronizado ts=1794147488` a 13.4 s de encender la salida
- status con hora_valida = true: a +54.3 s
- medida con ts: `{"v":30.9,"u":"°C","ts":1794147529}`, desfase -0.4 s respecto a la llegada
- SNTP bloqueado: internet=True sntp_blocked=True lan_blocked=True rules_ok=True reglas=16; tras reiniciar el DUT, 75 s: 2 «sntp: fallo», 0 sincronizaciones, hora_valida en los status: [False]
- SNTP desbloqueado: `I (79585) nodo: sntp: sincronizado ts=1794147624` a 5.0 s

**Resultado: PASS** — sincroniza a 13.4 s de encender la salida; con SNTP bloqueado 0 sincronizaciones y 2 fallos; desbloqueado sincroniza a 5.0 s
