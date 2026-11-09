# TC-CON-06 — Nunca vuelve al portal sin Wi-Fi

- imagen: `0.0.0-5d0699d-bench` (variante bench, run CI 42144808935)

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2`
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Reset con el AP del banco apagado; 15 min de observación y 5 escaneos
- log: `TC-CON-06-serie.log` (170 líneas)

## Resultado

- líneas con: 39 (destino distinto de CONECTANDO_WIFI: 0)
- última línea del DUT a los 890 s de su arranque
- escaneo a t=185 s: ningún clima-*
- escaneo a t=365 s: ningún clima-*
- escaneo a t=545 s: ningún clima-*
- escaneo a t=725 s: ningún clima-*
- escaneo a t=905 s: ningún clima-*

**Resultado: FAIL** — AssertionError: el nodo se reinició en la ventana
assert 17 <= 1
 +  where 17 = sum(<generator object test_tc_con_06_never_portal.<locals>.<genexpr> at 0x7663c2daa670>)
