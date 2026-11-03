# JRN-01.1 — Portal sin configuración

- slot: SLOT1; id esperado (FR-ID-01, MAC de dut.identity): `clima-f3c6d4`

- Precondiciones: AP del banco apagado (el escaneo comparte la radio)
- Reset y escaneo hasta ver clima-f3c6d4 (≤ 10 s)
- `con: ARRANQUE -> PORTAL` en el buffer a los 7.7 s

## Escaneos (solo SSID clima-*)

- t=12.3 s: ninguno
- t=16.9 s: [('clima-f3c6d4', 'OPEN')]

- log: `JRN-01.1-boot.log` (195 líneas)
- `clima-f3c6d4` visto a los 16.9 s (cota superior desde la petición de reset), auth OPEN

**Resultado: FAIL** — AssertionError: SSID a los 16.9 s > 10 s (T02/FR-POR-01)
assert 16.937500953674316 <= 10
