# TC-WDT-02 — Watchdog de tareas (wdt-test)

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (15:43:56.223 → 15:44:08.209 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Enviar «wdt-test» por la consola
- log: `TC-WDT-02-serie.log` (121 líneas)
- de «bloqueando medicion» a la línea boot: 29.1 s; reset=task_wdt

**Resultado: PASS** — reset=task_wdt a 29.1 s de «bloqueando medicion»
