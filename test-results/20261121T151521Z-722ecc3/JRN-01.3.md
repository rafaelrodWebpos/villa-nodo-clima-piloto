# JRN-01.3 — Unirse al Wi-Fi y log UDP

- el banco levanta el mismo AP desechable que el DUT guardó en JRN-01.2 (redactado)

- Precondiciones: AP y broker del banco apagados; el DUT quedó configurado (JRN-01.2)
- El banco levanta su AP desechable (canal 1) y resetea el DUT
- Observando 3 ciclos de medición (180 s) en el log serie y en el receptor UDP
- log: `JRN-01.3-serie.log` (199 líneas)
- log: `JRN-01.3-udp.log` (2000 líneas)
- T01: boot: → wifi: intento 1 en 190 ms (límite 2000 ms)
- 80 líneas serie tras obtener IP; perdidas 1, tarde 0; cortadas por la captura serie del banco (#89) y completas por UDP: 1 ['E (5073) transport_base: Failed to open a new conn']

**Resultado: FAIL** — AssertionError: 1 líneas serie sin copia UDP (FR-LOG-02)
assert not ['I (5083) nodo: con: CONECTANDO_BROKER -> CONECTANDO_BROKER (mqttI (8103) nodo: mqtt: intento 3']
