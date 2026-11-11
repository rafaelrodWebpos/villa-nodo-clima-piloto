# TC-OTA-07 — Comando OTA retained ignorado

- imagen: `0.0.0-6f30ae4-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (10:48:49.831 → 10:49:00.001 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Apagar el AP del banco (el DUT pierde la conexión; el broker sigue)
- Publicar con retain un comando válido (URL de una release v*)
- Encender el AP; esperar la reconexión (T11) y la entrega del retenido
- log: `TC-OTA-07-serie.log` (34 líneas)
- E8: sí; E7: 0; OTA_DESCARGA: 0; ota en status: ['ninguno']

**Resultado: PASS** — retenido ignorado con E8 al reconectar; sin E7 ni OTA_DESCARGA; ota = ninguno
