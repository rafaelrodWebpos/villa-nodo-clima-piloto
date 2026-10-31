# Peticiones de cambio al testbench

Son capacidades que este proyecto necesita y que el banco no reporta. Se
arreglan en el repositorio del testbench
(`github.com/SensorsIot/Embedded-AI-Harness`) y no en este proyecto. Mientras
siguen abiertas, la capacidad correspondiente del plan queda en `no` y los
tests que la necesitan aparecen bloqueados.

| ID | Capacidad del plan | Qué se pide | Por qué lo necesita este proyecto | Estado |
|---|---|---|---|---|
| CR-TB-01 | `bench-ap-internet` | Que el SoftAP del banco dé salida a Internet por NAT, al menos hacia `pool.ntp.org` (UDP/123), `github.com` y `release-assets.githubusercontent.com` (HTTPS), y que el banco reporte esa capacidad en su API | Fase 2: SNTP (FR-TIME-01, -03, -04, FR-MQTT-03; JRN-01.6). Fase 3: OTA contra releases reales de GitHub (JRN-02, FR-OTA-*). FSD §3.2, §3.3 y §22.0 | pedida por el propietario el 2026-10-31; la registra él en el repo del testbench |

Hay otras capacidades en `no` que se convertirán en peticiones cuando un test
de la ola que toque las necesite. Hasta entonces no se piden: `bench-sntp-block`
(FR-TIME-03/04/05), `bench-mqtt-auth` (FR-MQTT-07), `bench-traffic-capture`
(FR-LOG-01), `bench-dns-override` (FR-OTA-03), `bench-dual-console` (C-HW-08) y
`bench-power-cycle` (el operador lo cubre).
