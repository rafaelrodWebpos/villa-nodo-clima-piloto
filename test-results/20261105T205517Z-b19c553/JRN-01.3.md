# JRN-01.3 — Unirse al Wi-Fi y log UDP

- el banco levanta el mismo AP desechable que el DUT guardó en JRN-01.2 (redactado)

- Precondiciones: AP del banco apagado; el DUT quedó configurado (JRN-01.2)
- El banco levanta su AP desechable (canal 1) y resetea el DUT
- log: `JRN-01.3-serie.log` (113 líneas)
- log: `JRN-01.3-udp.log` (0 líneas)
- T01: boot: → wifi: intento 1 en 200 ms (límite 2000 ms)

**Resultado: FAIL** — AssertionError: falta con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up) en 30 s
assert None
