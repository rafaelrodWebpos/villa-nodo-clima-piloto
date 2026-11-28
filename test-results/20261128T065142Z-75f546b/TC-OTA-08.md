# TC-OTA-08 — Asset inexistente (error:http)

- imagen: `0.0.0-15ca457-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (06:56:34.284 → 06:56:46.669 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- OPERATIVO con salida a Internet; comando con un asset inexistente
- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- log: `TC-OTA-08-serie.log` (5 líneas)
- ota en status: ['en_curso', 'error:http']
- en_curso a 0.15 s
- T17: True; T20: True; líneas «ota: n %»: 0; reinicios: 0

**Resultado: PASS** — en_curso ≤ 2 s, T17, T20 y error:http; sin progreso ni reinicio
