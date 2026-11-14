# TC-OTA-13 — Periodo de medición durante la descarga

- imagen: `0.0.0-22fda6b-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (19:17:17.124 → 19:17:28.739 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- intervalos con una medida dentro de OTA_DESCARGA (s): [60.02, 60.03, 60.05]

**Resultado: PASS** — 3 intervalos en [55, 65] s: [60.02, 60.03, 60.05]
