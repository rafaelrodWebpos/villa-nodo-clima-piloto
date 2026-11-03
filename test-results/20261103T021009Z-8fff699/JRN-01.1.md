# JRN-01.1 — Portal sin configuración

- slot: SLOT1; id esperado (FR-ID-01, MAC de dut.identity): `clima-f3c6d4`

- Precondiciones: AP del banco apagado (el escaneo comparte la radio)
- Reset y escaneo hasta ver clima-f3c6d4 (≤ 10 s)

## Escaneos (solo SSID clima-*)

- t=4.6 s: ninguno
- t=9.2 s: [('clima-f3c6d4', 'OPEN')]

- log: `JRN-01.1-boot.log` (197 líneas)
- `clima-f3c6d4` visto a los 9.2 s (cota superior desde la petición de reset), auth OPEN
- FR-ID-01: reinicio 2 de 3
- log: `JRN-01.1-boot2.log` (97 líneas)
- FR-ID-01: reinicio 3 de 3
- log: `JRN-01.1-boot3.log` (97 líneas)
- ids en 3 arranques: ['clima-f3c6d4', 'clima-f3c6d4', 'clima-f3c6d4', 'clima-f3c6d4']

**Resultado: FAIL** — AssertionError: id inestable o ausente: ['clima-f3c6d4', 'clima-f3c6d4', 'clima-f3c6d4', 'clima-f3c6d4'] (FR-ID-01)
assert (4 == 3)
 +  where 4 = len(['clima-f3c6d4', 'clima-f3c6d4', 'clima-f3c6d4', 'clima-f3c6d4'])
