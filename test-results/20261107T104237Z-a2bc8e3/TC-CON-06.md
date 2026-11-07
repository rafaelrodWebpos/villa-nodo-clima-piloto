# TC-CON-06 — Nunca vuelve al portal sin Wi-Fi

- imagen: `0.0.0-a2bc8e3-bench` (variante bench, run CI 42365108439)

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2`
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Reset con el AP del banco apagado; 15 min de observación y 5 escaneos
- log: `TC-CON-06-serie.log` (111 líneas)

## Resultado

- líneas con: 39 (destino distinto de CONECTANDO_WIFI: 0)
- última línea del DUT a los 890 s de su arranque
- escaneo a t=185 s: ningún clima-*
- escaneo a t=365 s: ningún clima-*
- escaneo a t=545 s: ningún clima-*
- escaneo a t=725 s: ningún clima-*
- escaneo a t=905 s: ningún clima-*

**Resultado: PASS** — 39 líneas con:, todas hacia CONECTANDO_WIFI; el AP del portal no apareció en 5 escaneos
