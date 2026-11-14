# TC-OTA-12 — Comando durante la descarga (ocupado)

- imagen: `0.0.0-ada173a-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (14:07:51.761 → 14:08:02.292 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- ota en status: ['en_curso', 'rechazado:ocupado', 'ok', 'ninguno']; fw = B1: sí

**Resultado: PASS** — en_curso → rechazado:ocupado → ok y fw = B1
