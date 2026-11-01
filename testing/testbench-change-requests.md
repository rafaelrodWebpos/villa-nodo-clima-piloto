# Peticiones de cambio al testbench

Son capacidades que este proyecto necesita y que el banco no reporta. Se
arreglan en el repositorio del testbench
(`github.com/SensorsIot/Embedded-AI-Harness`) y no en este proyecto. Mientras
siguen abiertas, la capacidad correspondiente del plan queda en `no` y los
tests que la necesitan aparecen bloqueados.

| ID | Capacidad del plan | Qué se pide | Por qué lo necesita este proyecto | Estado |
|---|---|---|---|---|
| CR-TB-01 | `bench-ap-internet` | Que el SoftAP del banco dé salida a Internet por NAT, al menos hacia `pool.ntp.org` (UDP/123), `github.com` y `release-assets.githubusercontent.com` (HTTPS), y que el banco reporte esa capacidad en su API | Fase 2: SNTP (FR-TIME-01, -03, -04, FR-MQTT-03; JRN-01.6). Fase 3: OTA contra releases reales de GitHub (JRN-02, FR-OTA-*). FSD §3.2, §3.3 y §22.0 | pedida por el propietario el 2026-10-31; la registra él en el repo del testbench |
| CR-TB-02 | `bench-sntp-block` | Bloquear y desbloquear bajo demanda el UDP/123 (SNTP) que sale de la red del AP del banco, con la salida a Internet de CR-TB-01 activa, y que el banco reporte esa capacidad en su API | Fase 2: FR-TIME-03 (y FR-MQTT-03, que usa su contrato), FR-TIME-04 y FR-TIME-02 (fila bench⁺). FSD §3.2 y §13.2 | pedida por el propietario el 2026-10-31; la registra él en el repo del testbench |
| CR-TB-03 | `bench-mqtt-auth` | Arrancar el broker del banco con autenticación por usuario y contraseña (credenciales de prueba elegidas por el test) y que el banco reporte esa capacidad en su API | Fase 2: FR-MQTT-07 (credenciales erróneas y correctas). FSD §3.2 y §9.5 | pedida por el propietario el 2026-10-31; la registra él en el repo del testbench |
| CR-TB-04 | `bench-traffic-capture` | Capturar el tráfico UDP que sale del DUT en la red del AP del banco (destino, puerto, unicast o broadcast) durante una ventana, y que el banco reporte esa capacidad en su API | Fase 2: FR-LOG-01 y FR-LOG-02 (fila de captura). FSD §3.2 y §18.1 | pedida por el propietario el 2026-10-31; la registra él en el repo del testbench |
| CR-TB-05 | `bench-dns-override` | Que el DNS de la red del AP del banco resuelva un host elegido (p. ej., `github.com`) hacia un servidor HTTPS del banco con certificado autofirmado, y que el banco reporte esa capacidad en su API | Fase 3: FR-OTA-03 y T20 (tls). FSD §3.3, §7.4 y §22.0 | pedida por el propietario el 2026-10-31; la registra él en el repo del testbench |
| CR-TB-06 | `bench-wifi-ap`, `bench-wifi-ap-outage`, `bench-portal-driver` | Que `install.sh` desbloquee también la WiFi (`rfkill unblock wifi`; hoy solo lo hace con el Bluetooth) y que `/api/wifi/ap_status` informe de si la radio está bloqueada, en vez de responder `ok` con un AP que no puede arrancar | `POST /api/wifi/ap_start` falla con `rfkill: WLAN soft blocked` (2026-11-01). Sin AP quedan bloqueados JRN-01.2 en adelante (FR-POR-*, T01/T04/T05/T11) | encontrada por /commission el 2026-11-01; arreglo inmediato en el Pi: `sudo rfkill unblock wifi` (acto del propietario); la registra él en el repo del testbench |

Hay otras capacidades en `no` que no se piden todavía: `bench-dual-console`
(C-HW-08, fila bench; no está en los criterios de salida de ninguna fase),
`bench-power-cycle` (el operador lo cubre). `bench-serial-write` ya no está
en `no`: el banco la ofrece (`POST /api/serial/write`, ejercida el 2026-11-01).
