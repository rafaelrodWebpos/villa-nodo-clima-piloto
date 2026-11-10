# TC-POR-05 — Envío inválido por el portal

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-758ccbc-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (23:25:54.006 → 23:26:04.178 UTC)
- POST / con zona con mayúscula y #
- POST / con wifi_pass de 7 caracteres
- zona con mayúscula y #: HTTP 200 en 0.06 s (ida y vuelta por el relé); errores ['zona']
- wifi_pass de 7 caracteres: HTTP 200 en 0.04 s (ida y vuelta por el relé); errores ['wifi_pass']
- Reset: el DUT debe volver a PORTAL sin configuración escrita
- log: `TC-POR-05-log.log` (109 líneas)
- `con: PORTAL -> PORTAL (envío)`: 2 de 2 envíos
- `portal: POST / -> errores`: 2 de 2

**Resultado: PASS** — 2 envíos inválidos: error en su campo, sin NVS; reset → PORTAL
