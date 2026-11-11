# Plan de la Fase 3 — Actualización OTA (propuesta, sin empezar)

- **Estado:** APROBADO (H-86, 2026-11-10), con estas respuestas:
  - **D1:** sí; las pre-releases `ota-test-*` se publican solo desde un workflow de la CI.
  - **D2:** el primer tag es **v0.0.1**, como en H-37; v0.1.0 fue un error y no cambia nada.
  - **D3, D4, D5 y D6:** sí. D4: las 4 pruebas manuales de H-80 se repiten en la visita física final.
  - **D7:** sí; acciones actualizadas y fijadas por SHA, comprobando cada SHA contra su tag.
  - **Condición nueva, puerta S6:** el cambio completo del fork villa-2 lo revisa un auditor
    independiente, en solo lectura, ANTES de instalarlo en la Pi. Se prepara sin instalar y se
    avisa al propietario cuando esté listo.
  - El jueves 12 no se usa el banco ni se corren pruebas largas en la laptop (llega el SDR).
- **villa-2 listo para la revisión S6 (2026-11-10):** rama `villa-2` del fork
  `rafaelrodWebpos/Embedded-AI-Harness`, commit `dc00cbd` (un solo commit sobre villa-1, `8966260`),
  CI del fork en verde (run 42950087306). Sin tag y sin instalar. Ficheros: `pi/dns_override.py`,
  `pi/capture_controller.py`, `pi/mqtt_controller.py`, `pi/wifi_controller.py`, `pi/portal.py`,
  `pi/install.sh`, `pi/scripts/harness-volver-original.sh`, `pytest/testbench_driver.py`,
  `pytest/host/test_villa2.py`, `docs/fork-villa.md` y `docs/Harness-FSD.md`.
- **S6: «sí, con condiciones»** (informe del auditor fuera del repo). Correcciones H-87 en la rama
  `villa-2`, commit `a723456` encima de `dc00cbd`, CI del fork en verde (run 42998883166), sin
  instalar:
  - S6-01: token de la API.
  - S6-03: ficheros bajo `/run/harness`.
  - S6-04: INPUT de `eth0` hacia 192.168.4.0/24 descartado.
  - S6-05 a S6-09.
  - `harness-volver-original` lo deshace todo.
  - S6-02 (broker solo en 192.168.4.1) queda pendiente de decisión del propietario: cortaría al
    suscriptor MQTT de la laptop y al Home Assistant de prueba (H-52).
- **Base:** FSD 0.9.9 (§3.3, §7, §12, §19.3, §22.0); puerta S1 cerrada (H-85, `c27ebfc`).
- **Hoy en el repositorio:** de la Fase 3 solo hay dos pruebas declaradas, JRN-02.1 y JRN-02.2,
  sin implementar. No hay ninguna release ni pre-release publicada. El secreto `NODO_DENYLIST`
  está definido: la CI escanea los patrones de la instalación.

## 1. Requisitos y contratos de la Fase 3, en orden de implementación

Criterios de salida (§3.3): FR-OTA-*, NFR-OTA-01, FR-MQTT-09, NFR-SEC-02, C-BLD-04,
FR-CFG-01 (fila de OTA) y las filas T17–T23. Los nombres TC-OTA-nn son propuestos; se
declaran en el plan de pruebas al empezar cada bloque.

| # | Requisito / fila | Qué se implementa | Tests (nivel) |
|---|---|---|---|
| 1 | C-BLD-04 | `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y` y su comprobación en la CI sobre el `sdkconfig` generado. El bootloader nuevo se graba por el USB del banco, con la grabación normal: no hay acción física | TC-BLD-04 (CI) |
| 2 | FR-OTA-09 | Parser del payload `{"url": …}` (§12.1) | TC-OTA-01 (host) |
| 3 | FR-OTA-14, FR-OTA-02, FR-OTA-11, FR-OTA-13 | Política de URL pura, en este orden: análisis estricto → esquema y host → ruta del repo → `ota-test-*` solo en banco. También vale para cada redirección, con un máximo de 3 | TC-OTA-02 a TC-OTA-05 (host) |
| 4 | FR-OTA-05 (versión) | Comparación semver con anti-downgrade para `v*`, `misma_version`, y `ota-test-*` exentas en banco (H-84) | TC-OTA-06 (host) |
| 5 | FR-OTA-12 (clasificador) | Fallo de DNS, TCP o timeout → `error:red`; respuesta no 2xx → `error:http` | TC-OTA-07 (host) |
| 6 | T17–T23 (núcleo) | Filas de la tabla en `conectividad`, con OTA_DESCARGA y los eventos `cmd_ota` y `ota_ok/err` | TC-CON-01 ampliado (host) |
| 7 | FR-MQTT-09, §9.3 `ota` | Campo `ota` de `status`, que se publica en ≤ 2 s o, si no hay conexión, en el primer `status` tras T11 | TC-MQTT-02 ampliado (host); TC-OTA-08 (bench) |
| 8 | FR-OTA-01, FR-OTA-04 | Suscripción a `<sitio>/<zona>/<nodo>/cmd/ota`; un comando retained se ignora con E8 | TC-OTA-09 (bench), TC-OTA-10 (bench) |
| 9 | FR-OTA-03, FR-OTA-02 (adaptador) | `esp_https_ota` con el bundle de CA, comprobación del nombre del certificado y redirecciones validadas una a una | TC-OTA-11 (bench, `bench-dns-override`), JRN-02.1 |
| 10 | FR-OTA-05 (imagen), FR-OTA-06, T19 | Validación de la imagen (cabecera, chip, SHA-256), reinicio en el slot nuevo y `fw` = B en ≤ 120 s | TC-OTA-12 (bench⁺), JRN-02.1 |
| 11 | FR-OTA-07, T23, E9 | Validación en T11; rollback a los 300 s sin T11 | JRN-02.2 (bench⁺) |
| 12 | FR-OTA-08, T22, FR-OTA-12 (adaptador) | Abortar la descarga si cae el Wi-Fi o MQTT, conservando la imagen | TC-OTA-13 (bench⁺), TC-OTA-14 (bench⁺, 404) |
| 13 | FR-OTA-10, T21 | `rechazado:ocupado` durante una descarga | TC-OTA-15 (bench⁺) |
| 14 | T18 | Rechazos por payload, host y ruta, por el broker del banco | TC-OTA-16 (bench) |
| 15 | NFR-OTA-01 | Periodo de medición de 60 ± 5 s durante la descarga, alternando entre dos `ota-test-*` | TC-OTA-17 (bench⁺) |
| 16 | FR-CFG-01 (fila de OTA) | Tras una OTA A → B, B publica en los mismos tópicos | TC-OTA-18 (bench⁺) |
| 17 | NFR-SEC-02 | La CI descarga todas las releases y pre-releases publicadas y busca los patrones de `NODO_DENYLIST` con `strings` | TC-SEC-03 (CI) |
| 18 | FR-OTA-13 en la release | El job `verify` comprueba que la imagen del tag rechaza una `ota-test-*` | dentro de la verificación de release |

Todas las pruebas bench⁺ usan la imagen de banco y la salida a Internet del AP del fork (solo
direcciones públicas), según FR-OTA-13 y H-84. No hace falta el nivel field.

## 2. Capacidades del banco: una sola ampliación del fork (propuesta villa-2)

Faltan cinco capacidades: cuatro se resuelven en el fork y la quinta en este repositorio.

| Capacidad | Para | Diseño propuesto en el fork | Cómo se mantiene la LAN de la casa bloqueada |
|---|---|---|---|
| `bench-dns-override` (CR-TB-05) | FR-OTA-03, T20 (tls) | API `POST /api/wifi/dns_override {"host": "github.com", "enabled": bool}`: dnsmasq del AP resuelve ese host a 192.168.4.1. Un servidor HTTPS con certificado autofirmado (generado en la Pi, nunca versionado) escucha solo en 192.168.4.1:443 y solo mientras está activo | Apagado por defecto y en cada `ap_stop`, como la salida a Internet. Solo afecta a los clientes del AP. Las cadenas HARNESS_AP_FWD no cambian |
| `bench-mqtt-auth` (CR-TB-03) | FR-MQTT-07 | `POST /api/mqtt/start {"user": …, "pass": …}`: mosquitto con un fichero de contraseñas temporal, borrado al parar | El broker sigue escuchando solo para el AP y la API, como hoy |
| `bench-traffic-capture` (CR-TB-04) | FR-LOG-01, FR-LOG-02 (captura) | `POST /api/capture/start {"seconds": n}` y `GET /api/capture/result`: `tcpdump` solo en `wlan0` y solo para la MAC del DUT. Devuelve destino, puerto y tipo (unicast o broadcast), no el contenido | Solo la interfaz del AP; nunca `eth0` |
| `bench-serial-write` | FR-TIME-02 (bench⁺, TC-TIME-08), NFR-WDT-01 (fila target) | `POST /api/serial/write` ya existe (FR-030 del banco); el fork solo lo declara en `capabilities` | Sin red |
| `github-test-releases` (este repo) | JRN-02, FR-OTA-05/06/07/10, NFR-OTA-01 | Pre-releases `ota-test-*` publicadas por un workflow de la CI (ver decisión D1) | — |

- **Instalación:** una sola vez, con el mismo método que H-73. Te preparo los bloques de órdenes: A (instantánea y comprobación), B (instalación) y C (verificación). Tú los ejecutas, y `sudo harness-volver-original` lo deshace todo con una sola orden.
- **Paquetes nuevos en la Pi:** solo `tcpdump`, si no está; `openssl` ya viene con el sistema. Instalar algo en la Pi necesita tu aprobación (D6).
- **Regresión de la ampliación:**
  - FORK-01 a FORK-03 (LAN bloqueada, salida solo pública, restauración);
  - nuevas FORK-04 a FORK-07, una por capacidad, con control negativo hacia la LAN;
  - JRN-01.0 a 01.4 y TC-CON-14.
- **Pendientes de la Fase 2 que se desbloquean** con la ampliación: TC-TIME-08, NFR-WDT-01 (fila target), FR-MQTT-07, FR-LOG-01 (TC-LOG-04) y la fila de captura de FR-LOG-02. Se ejecutan y se anotan como adenda del cierre de la Fase 2.
- **No hace falta, ni se pide:** `bench-power-cycle` (cortes por instrumento), `bench-portal-dns` (CR-TB-09), `bench-dual-console`, `field-site`.

## 3. Decisiones que necesito del propietario

| # | Decisión | Propuesta |
|---|---|---|
| D1 | Publicar pre-releases `ota-test-*` en el repositorio público | Sí, solo desde un workflow de la CI (con `contents: write` solo en ese job). Imágenes de banco con versiones semver propias: B1, B2, sin-MQTT (FR-OTA-07), para esp32 no S3 y truncada (FR-OTA-05). Sin datos de la casa (NFR-SEC-02 las escanea). Marcadas como pre-release y con un nombre que diga «prueba» |
| D2 | Primer tag | **Resuelto (H-86): v0.0.1.** Texto de la propuesta: hay un conflicto: el plan registra `first_tag: v0.0.1` (H-37, 2026-11-03), y ahora dices v0.1.0. Propongo v0.1.0 como nuevo primer tag, sustituyendo a H-37, y que lo crees tú cuando la Fase 3 esté en verde |
| D3 | Tests con releases `v*` reales | En banco, las OTA de ida y vuelta usan `ota-test-*`. Los `v*` reales solo se usan en la verificación de la release. Así no hace falta publicar dos versiones `v*` solo para probar |
| D4 | Pruebas manuales en la visita final | Repetir, en la misma visita que el iPhone, las 4 manuales que quedaron como salvedad en H-80 (JRN-01.7, TC-CFG-02 y TC-MQTT-04 con cortes del USB-C, y TC-SEN-04 con SDA). El firmware ha cambiado desde entonces (S1 y Fase 3) |
| D5 | Runner self-hosted para la release (SEC-01) | Registrarlo solo durante la release y pararlo después, como dice §19.3 |
| D6 | Instalar `tcpdump` en la Pi | Sí, dentro de la instalación única del fork |
| D7 | Acciones de la CI en Node 20 | GitHub avisa de que las versiones v4 de checkout y de los artifacts usan Node 20 (obsoleto). Propongo pasar a sus versiones actuales, fijadas por SHA como en SEC-08, en un commit aparte durante el bloque 3 |

## 4. Acciones físicas y del propietario, agrupadas

| Sesión | Dónde | Qué | Duración |
|---|---|---|---|
| S-A, aprobación | chat | Decisiones D1 a D7 y aprobación del plan | — |
| S-B, instalación del fork | tu terminal (SSH a la Pi), sin tocar cables | Solo después de la revisión S6. Bloques A, B y C de la ampliación villa-2; luego yo corro la regresión | ~45 min tuyos |
| S-C, visita física única | junto al banco | (1) Prueba del iPhone de FR-POR-02 (H-83). (2) Si apruebas D4: cortes del USB-C de JRN-01.7, TC-CFG-02 (5 cortes) y TC-MQTT-04, y el SDA de TC-SEN-04, todo con avisos del banco | ~1 h 30 min |
| S-D, primer tag | tu terminal | Crear el tag v0.0.1 (D2, H-86) con el runner registrado (D5); la CI verifica y publica | ~30 min |

No hay ninguna acción física entre la instalación del fork y la visita final. Todas las pruebas
OTA se hacen por API (AP, broker, salida a Internet, DNS del banco).

## 5. Estimación por bloque

| Bloque | Contenido | Trabajo mío | Banco | Propietario |
|---|---|---|---|---|
| 0 | Aprobación (S-A) | — | — | decisiones |
| 1 | Código del fork villa-2, CI del fork, bloques de órdenes | 4–6 h | — | — |
| 2 | Instalación (S-B) y regresión del fork | 1 h | 1 h 30 min | 45 min |
| 3 | Pendientes de la Fase 2 con las capacidades nuevas | 2 h | 1 h 30 min | — |
| 4 | Núcleos puros y CI (filas 1–7 y 17 de la tabla del punto 1) | 5–6 h | — | — |
| 5 | Adaptadores OTA en el firmware (filas 8–13) | 8–10 h | — | — |
| 6 | Workflow de pre-releases `ota-test-*` y escaneo de NFR-SEC-02 | 3 h | — | aprobar D1 |
| 7 | Pruebas de banco de la Fase 3 y regresión de las Fases 1 y 2 | 6 h | 5–6 h | — |
| 8 | Visita física final (S-C) | 30 min | 1 h 30 min | 1 h 30 min |
| 9 | Verificación de release y primer tag (S-D) | 2 h | 1 h | 30 min |
| | **Total** | **~32–37 h** | **~12 h** | **~3 h 15 min** |

**Calendario orientativo:**
- **Miércoles 11:** aprobación y bloque 1.
- **Jueves 12:** llega el receptor SDR, que se prueba en la laptop y no en la Pi. Ese día solo hago trabajo sin banco ni acciones tuyas (bloques 4 y 5) y no lanzo pruebas largas que compitan con la laptop.
- **Viernes 13 o después:** instalación del fork (S-B) y bloques 2 y 3.
- **Semana siguiente:** bloques 6 y 7, la visita final (S-C) y el tag (S-D).

## Pausa por presupuesto hasta el sábado 2026-11-14 (H-88) — dónde quedó

- **Hecho:**
  - D7, C-BLD-04, núcleo de la política OTA (TC-OTA-01 a 04), T17–T23 en el núcleo y FR-MQTT-09 (TC-OTA-05).
  - Adaptador OTA, paso 1: `cmd/ota`, E8 y T18; TC-OTA-06 y TC-OTA-07 en verde (`459013c`, `6f30ae4`).
- **Fork villa-2:** completo en `bb1ec0e` (rama `villa-2`), sin instalar. Pendiente:
  - que el propietario confirme S6-02 tal como quedó (todas las interfaces y la cadena `HARNESS_MQTT_IN` solo para la laptop);
  - que Claude lo verifique y dé los pasos 1–8 de `docs/fork-villa.md`.
- **Rama `driver-fork-villa-2`:** se fusiona justo después de instalar.
- **Siguiente al volver:** la descarga OTA (T17 con `esp_https_ota`, redirecciones validadas, versión, progreso, T19/T20/T22) y T23. Después, el workflow de las pre-releases `ota-test-*`.
- **Banco libre al pausar:** AP y broker apagados, salida a Internet apagada, SNTP desbloqueado.
