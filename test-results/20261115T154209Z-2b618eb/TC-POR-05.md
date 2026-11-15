# TC-POR-05 — Envío inválido por el portal

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-b2fffa7-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (15:44:24.936 → 15:44:36.281 UTC)
- POST / con zona con mayúscula y #
- POST / con wifi_pass de 7 caracteres
- zona con mayúscula y #: HTTP 200 en 0.07 s (ida y vuelta por el relé); errores ['zona']
- wifi_pass de 7 caracteres: HTTP 200 en 0.05 s (ida y vuelta por el relé); errores ['wifi_pass']
- Reset: el DUT debe volver a PORTAL sin configuración escrita
- log: `TC-POR-05-log.log` (108 líneas)
- `con: PORTAL -> PORTAL (envío)`: 2 de 2 envíos
- `portal: POST / -> errores`: 2 de 2

**Resultado: PASS** — 2 envíos inválidos: error en su campo, sin NVS; reset → PORTAL
