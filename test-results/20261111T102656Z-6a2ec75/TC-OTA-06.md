# TC-OTA-06 — Rechazos de comandos OTA (T18)

- imagen: `0.0.0-6a2ec75-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (10:35:33.002 → 10:35:44.498 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Publicar en cmd/ota un comando que debe dar rechazado:payload
- rechazado:payload: status a —; E7 sí; E0 sí
- Publicar en cmd/ota un comando que debe dar rechazado:host
- rechazado:host: status a —; E7 sí; E0 sí
- Publicar en cmd/ota un comando que debe dar rechazado:ruta
- rechazado:ruta: status a —; E7 sí; E0 sí
- log: `TC-OTA-06-serie.log` (207 líneas)

**Resultado: FAIL** — AssertionError: ningún status con ota=rechazado:payload
assert None is not None
