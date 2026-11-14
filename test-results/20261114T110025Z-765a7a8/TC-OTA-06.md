# TC-OTA-06 — Rechazos de comandos OTA (T18)

- imagen: `0.0.0-765a7a8-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (11:01:33.403 → 11:01:43.921 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Publicar en cmd/ota un comando que debe dar rechazado:payload
- rechazado:payload: status a 0.24 s; E7 sí; E0 sí
- Publicar en cmd/ota un comando que debe dar rechazado:host
- rechazado:host: status a 0.25 s; E7 sí; E0 sí
- Publicar en cmd/ota un comando que debe dar rechazado:ruta
- rechazado:ruta: status a 0.27 s; E7 sí; E0 sí
- log: `TC-OTA-06-serie.log` (192 líneas)

**Resultado: PASS** — rechazado:payload, :host y :ruta en 0.24 s, 0.25 s, 0.27 s; E7 y E0 en los tres; sin OTA_DESCARGA
