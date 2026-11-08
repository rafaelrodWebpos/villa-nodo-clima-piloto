# TC-TIME-05 — Medir y publicar sin hora

- imagen: `0.0.0-ef118af-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (02:23:44.442 → 02:23:56.285 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- AP del banco sin salida a Internet: SNTP inalcanzable desde el arranque

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- log: `TC-TIME-05-serie.log` (186 líneas)
- log: `TC-TIME-05-mqtt.log` (7 líneas)

## Resultado

- primer status de la última sesión: uptime_s=4, hora_valida=False
- primera medida: `<base>/temperatura` {"v":29.8,"u":"°C","ts":null} a 6.1 s del encendido estimado

**Resultado: PASS** — primera medida a 6.1 s del encendido estimado con ts=null; hora_valida=false
