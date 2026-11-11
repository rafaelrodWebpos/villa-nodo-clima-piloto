# TC-POR-09 — Clave Wi-Fi errónea

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-fc5103a-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (02:08:16.588 → 02:08:26.360 UTC)
- POST / válido con la clave errónea del AP desechable del banco
- respuesta al envío: HTTP 200, probando=True
- El banco levanta su AP desechable (canal 1) con la clave correcta
- T06 a los 20.0 s de T04 (límite 20 s + 5 s por el cambio de canal)
- El AP del portal sigue visible: el banco vuelve a unirse y pide /
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (02:08:49.375 → 02:09:02.351 UTC)
- GET / tras T06: HTTP 200, no-conecta=True
- Reset: la NVS sigue sin configuración
- log: `TC-POR-09-log.log` (134 líneas)

**Resultado: PASS** — clave errónea: T06 a los 20.0 s, AP visible, «no se pudo conectar», NVS sin cambios
