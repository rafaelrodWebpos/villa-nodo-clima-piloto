# TC-POR-07 — Redirecciones del portal cautivo

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-a2bc8e3-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `169.254.138.107`
- El banco se une al AP abierto clima-f3c6d4 (intento 2)
- sta_join intento 2: ip del banco `192.168.4.2`
- GET http://192.168.4.1/generate_204

**Resultado: FAIL** — CommandError: http: HTTP request failed: timed out
