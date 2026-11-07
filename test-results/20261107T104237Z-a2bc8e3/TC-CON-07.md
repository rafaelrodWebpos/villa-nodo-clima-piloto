# TC-CON-07 — Ocupado mientras valida

- imagen: `0.0.0-a2bc8e3-bench` (variante bench, run CI 42365108439)
- red del envío: ficticia (`red-que-no-existe`), así que el DUT sigue en VALIDANDO hasta T06

- Precondiciones: grabar la imagen de la CI en SLOT1, P-NVS-ERASE y PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2`
- Primer POST / válido (T04) y, enseguida, un segundo POST (T07)
- log: `TC-CON-07-serie.log` (25 líneas)

## Resultado

- 1.er POST: HTTP 200, probando=True
- 2.º POST: HTTP 200, ocupado=True
- líneas T04: 1, T07: 1, «wifi: intento 1»: 1
- T06 al final: sí

**Resultado: PASS** — el segundo envío en VALIDANDO respondió «ocupado», con su línea T07 y sin segunda prueba
