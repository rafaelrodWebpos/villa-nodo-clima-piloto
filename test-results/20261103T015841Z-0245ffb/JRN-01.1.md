# JRN-01.1 — Portal sin configuración

- slot: SLOT1; id esperado (FR-ID-01, MAC de dut.identity): `clima-f3c6d4`

- Precondiciones: AP del banco apagado (el escaneo comparte la radio)
- Reset y escaneo hasta ver clima-f3c6d4 (≤ 10 s)

## Escaneos (solo SSID clima-*)

- t=4.6 s: ninguno
- t=9.2 s: ninguno
- t=13.8 s: ninguno
- t=18.4 s: ninguno
- t=23.1 s: ninguno

- log: `JRN-01.1-boot.log` (167 líneas)

**Resultado: FAIL** — AssertionError: clima-f3c6d4 no apareció en 5 escaneos (20 s)
assert None
