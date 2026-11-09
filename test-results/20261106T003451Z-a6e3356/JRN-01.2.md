# JRN-01.2 — Aprovisionar por el portal

- AP desechable del banco con SSID y clave aleatorios de esta ejecución (redactados en la evidencia)
- broker `broker.local`, sitio `sitio1`, zona `zona1` (ficticios, NFR-SEC-01)

- Precondiciones: AP del banco apagado; el DUT sigue en PORTAL (JRN-01.1)
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2`
- POST / con los datos del AP desechable
- respuesta al envío: HTTP 200, probando=True
- El banco levanta su AP desechable (canal 1); el DUT debe unirse, guardar y reiniciar
- log: `JRN-01.2-log.log` (84 líneas)

**Resultado: FAIL** — AssertionError: el DUT no reinició tras T05
assert (None)
