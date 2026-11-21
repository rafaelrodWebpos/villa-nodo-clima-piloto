# TC-OTA-10 — Imágenes inválidas (error:imagen)

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (16:22:28.483 → 16:22:39.272 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Comando con firmware_esp32.bin
- firmware_esp32.bin: error:imagen a 5.1 s
- Comando con firmware_truncada.bin
- firmware_truncada.bin: error:imagen a 15.2 s
- log: `TC-OTA-10-serie.log` (42 líneas)

**Resultado: PASS** — esp32 y truncada: error:imagen, sin reinicio
