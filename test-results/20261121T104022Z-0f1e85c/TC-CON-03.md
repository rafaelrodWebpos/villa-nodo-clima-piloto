# TC-CON-03 — Backoff de Wi-Fi con el AP apagado

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (10:41:01.932 → 10:41:12.254 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Reset con el AP del banco apagado; observación de 10 reintentos (≈ 6 min)
- log: `TC-CON-03-serie.log` (71 líneas)

## Resultado

- líneas T09: 9, T10: 10
- intervalo 1: 1.0 s (esperado 1 s ± 10 %)
- intervalo 2: 4.0 s (esperado 2 s ± 10 %)
- intervalo 3: 8.0 s (esperado 4 s ± 10 %)
- intervalo 4: 16.0 s (esperado 8 s ± 10 %)
- intervalo 5: 32.0 s (esperado 16 s ± 10 %)
- intervalo 6: 60.0 s (esperado 32 s ± 10 %)
- intervalo 7: 60.0 s (esperado 60 s ± 10 %)
- intervalo 8: 60.0 s (esperado 60 s ± 10 %)
- intervalo 9: 60.0 s (esperado 60 s ± 10 %)

**Resultado: FAIL** — AssertionError: solo 9 intervalos medidos
assert 9 == 10
 +  where 9 = len([1.0, 4.0, 8.0, 16.0, 32.0, 60.0, ...])
 +  and   10 = len([1, 2, 4, 8, 16, 32, ...])
