# TC-OTA-09 — Certificado no confiable (error:tls)

- imagen: `0.0.0-765a7a8-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (11:07:14.830 → 11:07:25.503 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- OPERATIVO sin Internet; DNS del banco: github.com -> HTTPS autofirmado (bench-dns-override)
- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- log: `TC-OTA-09-serie.log` (8 líneas)
- ota en status: ['en_curso', 'error:tls']
- en_curso a 0.23 s
- T17: True; T20: True; líneas «ota: n %»: 0; reinicios: 0

**Resultado: PASS** — T17, T20 y error:tls sin ninguna línea «ota: n %»; sin reinicio
