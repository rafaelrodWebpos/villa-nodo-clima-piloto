# JRN-01.1 — Portal sin configuración

- slot: SLOT1; id esperado (FR-ID-01, MAC de dut.identity): `clima-f3c6d4`

- Precondiciones: AP del banco apagado (el escaneo comparte la radio)

**Resultado: FAIL** — AssertionError: el AP del banco está activo: el escaneo no puede correr (no se apaga aquí: no es nuestro)
assert not True
 +  where True = <built-in method get of dict object at 0x7b91a09b8b40>('active')
 +    where <built-in method get of dict object at 0x7b91a09b8b40> = {'active': True, 'channel': 1, 'internet': False, 'sntp_blocked': False, ...}.get
 +      where {'active': True, 'channel': 1, 'internet': False, 'sntp_blocked': False, ...} = ap_status()
 +        where ap_status = <testbench_driver.TestbenchDriver object at 0x7b91a1216ff0>.ap_status
