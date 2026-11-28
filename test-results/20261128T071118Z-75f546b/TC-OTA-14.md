# TC-OTA-14 — Producción rechaza una pre-release ota-test-*

- imagen: `0.0.0-15ca457` (variante production, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (07:11:58.207 → 07:12:08.436 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Publicar en cmd/ota la URL de ota-test-2
- log: `TC-OTA-14-serie.log` (122 líneas)
- 0.0.0-15ca457 (producción): status ota = rechazado:ruta a 0.03 s; OTA_DESCARGA: no

**Resultado: PASS** — rechazado:ruta a 0.03 s; sin OTA_DESCARGA
