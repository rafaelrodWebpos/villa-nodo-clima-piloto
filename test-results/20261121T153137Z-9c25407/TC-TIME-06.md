# TC-TIME-06 — Reintento SNTP sin hora

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (15:33:36.623 → 15:33:47.894 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- AP del banco sin salida a Internet: SNTP inalcanzable

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Observar la consola 5 min con IP
- log: `TC-TIME-06-serie.log` (111 líneas)

## Resultado

- primera «sntp: inicio» a 0.5 s de wifi_up
- «sntp: inicio» en los 5 min: 30; intervalos (s): [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
- «sntp: fallo» en la captura: 10
- servidor: pool.ntp.org

**Resultado: PASS** — 30 peticiones en 5 min, intervalo máximo 10.0 s
