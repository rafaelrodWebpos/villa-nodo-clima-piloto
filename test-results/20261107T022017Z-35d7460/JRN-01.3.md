# JRN-01.3 — Unirse al Wi-Fi y log UDP

- el banco levanta el mismo AP desechable que el DUT guardó en JRN-01.2 (redactado)

- Precondiciones: AP y broker del banco apagados; el DUT quedó configurado (JRN-01.2)
- El banco levanta su AP desechable (canal 1) y resetea el DUT
- Observando 3 ciclos de medición (180 s) en el log serie y en el receptor UDP
- log: `JRN-01.3-serie.log` (271 líneas)
- log: `JRN-01.3-udp.log` (229 líneas)
- T01: boot: → wifi: intento 1 en 200 ms (límite 2000 ms)
- 161 líneas serie tras obtener IP; perdidas 80, tarde 0

**Resultado: FAIL** — AssertionError: 80 líneas serie sin copia UDP (FR-LOG-02)
assert not ['I (1808) nodo: mqtt: intento 1', 'I (372) cpu_start: Multicore app', 'I (380) cpu_start: GPIO 44 and 43 are used as ...o cpu start user code', 'I (382) cpu_start: cpu freq: 160000000 Hz', 'I (383) app_init: Application information:', ...]
