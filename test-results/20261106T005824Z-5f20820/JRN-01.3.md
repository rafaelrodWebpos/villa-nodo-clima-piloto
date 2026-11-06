# JRN-01.3 — Unirse al Wi-Fi y log UDP

- el banco levanta el mismo AP desechable que el DUT guardó en JRN-01.2 (redactado)

- Precondiciones: AP del banco apagado; el DUT quedó configurado (JRN-01.2)
- El banco levanta su AP desechable (canal 1) y resetea el DUT
- Observando 3 ciclos de medición (180 s) en el log serie y en el receptor UDP
- log: `JRN-01.3-serie.log` (175 líneas)
- log: `JRN-01.3-udp.log` (26 líneas)
- T01: boot: → wifi: intento 1 en 210 ms (límite 2000 ms)

**Resultado: FAIL** — AssertionError: el receptor UDP no recibió UDP logging -> <host>:<port> (E11)
assert False
 +  where False = any(<generator object test_jrn_01_3_wifi_and_udp_log.<locals>.<genexpr> at 0x72f7e20973e0>)
