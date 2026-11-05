# TC-POR-07 — Redirecciones del portal cautivo

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2`
- GET http://192.168.4.1/generate_204
- GET http://192.168.4.1/hotspot-detect.html
- /generate_204: respuesta final HTTP 200, 3502 bytes, formulario=True
- /hotspot-detect.html: respuesta final HTTP 200, 3502 bytes, formulario=True

**Resultado: PASS** — /generate_204 y /hotspot-detect.html terminan en el formulario del portal
