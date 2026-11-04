# TC-POR-05 — Envío inválido por el portal

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-bench`
- El banco se une al AP abierto clima-f3c6d4
- POST / con zona con mayúscula y #

**Resultado: FAIL** — CommandError: http: HTTP request failed: timed out
