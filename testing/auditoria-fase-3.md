# Encargo de auditoría independiente — cierre de la Fase 3 (S1 de cierre y S3)

- **Pedido por:** el propietario (2026-11-15), después de la visita física final.
- **Auditor:** independiente del desarrollo. Revisa con ojos de atacante, igual que en
  `testing/auditoria-seguridad-fase-2.md` y `testing/verificacion-seguridad-fase-2.md`.
- **Método:** solo lectura del código, la configuración, la CI y la evidencia del repositorio.
- **Base:** rama `main` en `9d637d7` (FSD 0.9.11) o en el commit que añade este encargo.
- **Diff a revisar entero:** `c27ebfc..HEAD`. `c27ebfc` es el cierre de la puerta S1 (H-85).
- **Después:** el tag v0.0.1, que lo crea el propietario. La auditoría no lo crea.

## 1. S1 de cierre de la Fase 3

Repetir la revisión de S1 sobre todo lo que cambió desde `c27ebfc`. Hay que confirmar que los
hallazgos de la Fase 2 siguen cerrados y que no hay puertas traseras nuevas.

| Qué | Commits | Qué comprobar |
|---|---|---|
| **DNS del portal (cambió SEC-06)** | `b2fffa7`; FSD 0.9.11 en `9d637d7` | `components/portal/portal_dns.c`, `portal_origen.c` y `main.c` (`indice_ap`, `arrancar_portal`); `CONFIG_LWIP_NETBUF_RECVINFO=y`. El socket escucha en `INADDR_ANY`; se contesta solo si `IP_PKTINFO` da destino 192.168.4.1, la interfaz de entrada es la del AP y el origen está en 192.168.4.0/24. Sin `IP_PKTINFO` no se contesta. Buscar cualquier camino por el que una consulta que llega por el STA en VALIDANDO, o dirigida a la IP del STA, reciba respuesta. Revisar también el índice 0 y el cambio de índice si el AP se reinicia. Prueba: TC-POR-14 (host) |
| **Comandos serie E13 por USB-Serial/JTAG** | `6d274d6`; FSD 0.9.10 | Solo con `CONFIG_NODO_BENCH_BUILD`. La imagen de producción no lee la consola (C-LOG-02, `c_log_02` de la CI) |
| **Imagen de prueba sin MQTT** | `6c3fc5f` | `CONFIG_NODO_TEST_SIN_MQTT` y `sdkconfig.ota-test-sin-mqtt.defaults`: que no pueda acabar en una imagen de producción ni en un tag |
| **CI** | `006d69f`, `6c3fc5f`, `bb814d2`, `80c9618`, `09b635e`, `ddaac8d` | Acciones fijadas por SHA. `ota-test.yml`: `contents: write` solo en el job de publicación, entrada `serie` validada y escaneo NFR-SEC-02 antes de publicar (TC-SEC-03). Job `verify` de `build.yml`: TC-OTA-14 sin skip y `set -o pipefail`. Driver del fork fijado con su sha256 |
| **Riesgos aceptados de §19.3** | — | Que sigan siendo ciertos con la OTA real: SEC-01, SEC-02, SEC-12 a SEC-15, SEC-08 |

## 2. S3: cadena OTA

| Qué | Dónde | Qué comprobar |
|---|---|---|
| **Política pura** | `components/ota/ota_politica.c` (`464a807`, `d579873`); tests `tests/host/test_ota_politica.c` (TC-OTA-01 a 04, 06, 07) | Payload de §12.1. Análisis estricto de la URL (FR-OTA-14) en la URL inicial y en cada redirección (máximo 3). Hosts y ruta del repo (FR-OTA-02/11). Tamaño de los saltos (2048). Clasificación de fallos (FR-OTA-12) |
| **Anti-downgrade (FR-OTA-05)** | `ota_version` en `ota_politica.c`; llamada en `ota_descarga.c:descargar` | Semver para las `v*`: igual da `misma_version` y anterior da `version_anterior`. La comprobación ocurre **antes de escribir** en la partición. Revisar sufijos raros, números enormes y versiones sin parchear |
| **Rechazo de `ota-test-*` (FR-OTA-13)** | `ota_url_inicial` en `ota_politica.c`, con el indicador `IMAGEN_BANCO` de `main.c:96-99` (true solo con `CONFIG_NODO_BENCH_BUILD`); `bb814d2` | En producción, toda URL inicial de `…/releases/download/ota-test-*/…` da `rechazado:ruta`. Comprobar que `ota_url_redireccion` no tiene ningún camino para llegar a una `ota-test-*` desde una URL inicial `v*`. Evidencia: TC-OTA-14 sobre la imagen de producción (`test-results/20261114T192518Z-bb814d2/`) y su paso en `verify` |
| **Adaptador de descarga** | `components/ota/ota_descarga.c` (`765a7a8`, `498db4f`, `4ea2a53`, `b041244`) | Redirecciones a mano: la `Location` se captura con `HTTP_EVENT_ON_HEADER` y se valida antes de seguirla. Bundle de CA y nombre del certificado (FR-OTA-03; TC-OTA-09 con `dns_override`). Búferes (`buffer_size`, `buffer_size_tx`, `URL_SALTO_MAX`) sin desbordes ni truncados aceptados. El aborto de T22. Nada se marca arrancable antes de `esp_https_ota_finish` |
| **Máquina de estados y main** | `main/main.c` (`comando_ota`, acciones de T17 a T23; `7ac28aa`, `e899df8`, `57c7eb3`) | Comandos retained ignorados (E8, FR-OTA-04). Un segundo comando da `rechazado:ocupado`. T19: el status con `ok`, luego el offline, luego el reinicio. T22: aborto si cae el Wi-Fi o MQTT |
| **Rollback (FR-OTA-07, T23, C-BLD-04)** | `89a9f7b` (`CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE`); `main.c` (temporizador de 300 s, validación en T11) | La imagen nueva solo se marca válida tras T11. Si pasan 300 s sin T11, `esp_ota_mark_app_invalid_rollback_and_reboot`. Revisar que ningún camino marque válida una imagen que no llegó a OPERATIVO. Evidencia: JRN-02.2 (`test-results/20261114T185438Z-22fda6b/`) |
| **Corte de alimentación durante la descarga (TC-OTA-15, H-89)** | `tests/bench/test_jrn02.py` (`fad73ef`, `2b618eb`) | Que la prueba demuestra lo que dice: corte con la escritura al 50 %; arranca A con `reset=poweron`; el primer status lleva `fw` = A; 330 s sin rollback. El primer intento salió FAIL por un defecto de la prueba y el segundo not done; los dos están en el historial de la fila |
| **Pre-releases** | `.github/workflows/ota-test.yml`; release `ota-test-2` | Solo desde la CI. Las imágenes llevan versiones propias y no superan a una `v*`. El escaneo NFR-SEC-02 corre antes de publicar |

## 3. Qué no tocar

- **El repositorio:** no hacer commit ni push, no crear ramas, tags ni releases, no borrar pre-releases.
- **Documentos protegidos:** no editar `testing/gates/*`, el FSD, `components/portal` ni el plan de pruebas.
- **El banco:** no llamar a su API, no grabar, no capturar tráfico y no conectarse a su IP.
- **Secretos:** no leer el `.env` ni el token del banco, y no copiar en el informe IP ni MAC distintas de 192.168.4.x y las del DUT.
- **El fork del banco** (`Embedded-AI-Harness-villa`): queda fuera del alcance; lo revisó la puerta S6.
- **Las acciones del propietario:** no crear el tag v0.0.1 ni lanzar los jobs `verify`/`release`.

## 4. Entrega

- **El informe:** se entrega al propietario fuera del repositorio, como en S6, y él decide si se versiona.
- **Formato:** el mismo de `testing/auditoria-seguridad-fase-2.md`. Una tabla con ID, severidad, ámbito (P, B o CI), `archivo:línea`, escenario de ataque concreto y recomendación.
- **Veredictos:**
  - si hay o no puerta trasera en `c27ebfc..HEAD`;
  - S1 de cierre: sí, no o sí con condiciones;
  - S3: sí, no o sí con condiciones.
- **Los hallazgos:** los numera el propietario; el auditor usa IDs provisionales.
