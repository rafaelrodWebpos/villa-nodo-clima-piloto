# JRN-01.3 — Unirse al Wi-Fi y log UDP

- el banco levanta el mismo AP desechable que el DUT guardó en JRN-01.2 (redactado)

- Precondiciones: AP y broker del banco apagados; el DUT quedó configurado (JRN-01.2)
- El banco levanta su AP desechable (canal 1) y resetea el DUT
- Observando 3 ciclos de medición (180 s) en el log serie y en el receptor UDP
- log: `JRN-01.3-serie.log` (266 líneas)
- log: `JRN-01.3-udp.log` (570 líneas)
- T01: boot: → wifi: intento 1 en 200 ms (límite 2000 ms)
- 156 líneas serie tras obtener IP; perdidas 74, tarde 0

**Resultado: FAIL** — AssertionError: 74 líneas serie sin copia UDP (FR-LOG-02)
assert not ['I (387) app_init: Project name:     nodo_clima', 'I (391) app_init: App version:      0.0.0-04afc57-bench', 'I (396)...HA256:  e406ca704...', 'I (405) app_init: ESP-IDF:          v6.0.2', 'I (409) efuse_init: Min chip rev:     v0.0', ...]
