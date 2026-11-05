# TC-POR-07 — Redirecciones del portal cautivo

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `169.254.138.107`
- El banco se une al AP abierto clima-f3c6d4 (intento 2)
- sta_join intento 2: ip del banco `192.168.4.3`
- GET http://192.168.4.1/generate_204
- GET http://192.168.4.1/hotspot-detect.html
- /generate_204: respuesta final HTTP 404, 29 bytes, formulario=False

**Resultado: FAIL** — AssertionError: /generate_204: la respuesta final no es el formulario del portal (HTTP 404)
assert (404 == 200)
 +  where 404 = Response(status_code=404, headers={'Content-Type': 'text/html', 'Content-Length': '29'}, _body_bytes=b'Nothing matches the given URI').status_code
