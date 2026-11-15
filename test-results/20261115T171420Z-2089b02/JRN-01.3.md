# JRN-01.3 — Unirse al Wi-Fi y log UDP

- el banco levanta el mismo AP desechable que el DUT guardó en JRN-01.2 (redactado)

- Precondiciones: AP y broker del banco apagados; el DUT quedó configurado (JRN-01.2)
- El banco levanta su AP desechable (canal 1) y resetea el DUT
- Observando 3 ciclos de medición (180 s) en el log serie y en el receptor UDP
- log: `JRN-01.3-serie.log` (283 líneas)
- log: `JRN-01.3-udp.log` (561 líneas)
- T01: boot: → wifi: intento 1 en 200 ms (límite 2000 ms)
- producción: 0 líneas en el receptor UDP en 3 ciclos; 4 med: en la consola

**Resultado: PASS** — T01 en 200 ms, unido al AP del banco; producción sin log UDP en 3 ciclos
