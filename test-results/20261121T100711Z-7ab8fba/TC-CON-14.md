# TC-CON-14 — AP abierto gemelo (evil twin) rechazado

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (10:34:12.419 → 10:34:23.624 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- AP gemelo: el mismo SSID de prueba de esta ejecución, abierto, 180 s (nunca el SSID de la casa, H-83)

- Resetear el DUT y levantar el AP ABIERTO gemelo con el SSID de prueba (180 s)
- con el gemelo abierto: 8 líneas `wifi: intento`; T08: 0; MAC del DUT entre las estaciones del AP: no
- Apagar el gemelo y levantar el AP con clave; esperar T08
- log: `TC-CON-14-serie.log` (155 líneas)
- con el AP con clave: T08 a 13.2 s

**Resultado: PASS** — gemelo abierto rechazado 180 s (8 intentos, sin asociación); con clave, T08 a 13.2 s
