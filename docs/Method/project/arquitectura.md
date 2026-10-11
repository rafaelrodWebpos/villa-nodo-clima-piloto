# Nodo Clima Piloto — Reglas del proyecto

Lo propio de este proyecto. Las capas y los componentes están definidos en el
FSD §2.4; aquí se dice cómo los refleja el código.

## Plataforma de build

- **ESP-IDF 6.x**, target `esp32s3`. La versión exacta queda fijada en la
  imagen de CI y en el devcontainer (`/harness`); se commitea
  `dependencies.lock`, no `managed_components/`.
- `cmake_minimum_required(VERSION 3.22)`.
- **Componentes gestionados** (`main/idf_component.yml`): se declaran solo en la
  fase que los usa, nunca de forma especulativa.
  - Fase 2: `espressif/mqtt`; `espressif/cjson` si se usa cJSON para serializar.
  - Fase 3: ninguno extra (`esp_https_ota` y el bundle de certificados vienen
    con ESP-IDF).
- Configuración: `sdkconfig.defaults` commiteado; `sdkconfig` generado, no.
  Debe fijar:
  - flash de 8 MB sin autodetección y la tabla `partitions.csv` del FSD §2.2;
  - `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE` (FR-OTA-07);
  - `CONFIG_MBEDTLS_CERTIFICATE_BUNDLE` (FR-OTA-03);
  - `CONFIG_ESP_TASK_WDT_PANIC` con un timeout de 30 s (NFR-WDT-01);
  - la PSRAM deshabilitada (C-HW-03).
- La versión de la aplicación sale del tag de git (`git describe`) y la fecha
  de build se incrusta para FR-TIME-02.
- `ota_repo` (FR-OTA-11) es una opción de Kconfig con valor por defecto
  `rafaelrodWebpos/villa-nodo-clima-piloto`; no es un secreto.

## Estructura de fuentes (refleja las capas)

```text
main/                 raíz de composición: crea tareas y conecta callbacks
components/
  medicion/           L2  ciclo de medición, punto de rocío (núcleo puro)
  conectividad/       L2  máquina de estados (tabla pura + adaptadores)
  ota_politica/       L2  política de URL/versión (pura)
  sht41/              L1  driver; conversión y CRC puros
  publicador/         L1  tópicos y serializador JSON (puros) + esp-mqtt
  ha_discovery/       L1  generador de configuración (puro)
  portal/             L1  HTTP + DNS; validador del §17 (puro)
  ota_cmd/            L1  parser de comandos (puro) + esp_https_ota
  hora/               L1  regla de validez (pura) + SNTP
  identidad/          L1  id desde la MAC (puro)
tests/host/           tests de los núcleos puros (compilador nativo)
tests/target/         tests Unity en el dispositivo
tests/bench/          pytest contra el testbench
```

- Las capas inferiores nunca incluyen cabeceras de las superiores.
- Cada núcleo puro compila sin ESP-IDF (`tests/host`).
- Los comandos de inyección de fallos (NFR-WDT-01) solo existen en el build de
  pruebas (`CONFIG_NODO_TEST_HOOKS`) y la CI comprueba que el build de release
  no los contiene.

## Repositorio público — prohibiciones

- Ningún SSID, contraseña, host o IP de broker, zona real ni coordenada en el
  código, en Kconfig, en `sdkconfig.defaults`, en los tests, en los fixtures,
  en los logs commiteados ni en `test-results/`.
- Los valores del banco se leen de variables de entorno
  (`NODO_TEST_WIFI_SSID`, `NODO_TEST_WIFI_PASS`, `NODO_TEST_MQTT_*`) y nunca
  se escriben en la evidencia: se redactan antes de guardar.
- La CI ejecuta un escáner de secretos sobre el árbol y el historial
  (NFR-SEC-01) y `strings` sobre el binario de release (NFR-SEC-02).

## Imágenes

| Imagen | Defaults | Lleva | Uso |
|---|---|---|---|
| producción | `sdkconfig.defaults` | sin log UDP ni ganchos de prueba | releases `v*.*.*`, journey de release-verify |
| banco | `sdkconfig.defaults;sdkconfig.bench.defaults` | `CONFIG_NODO_BENCH_BUILD`, log UDP hacia el testbench, marcador `NODO-BENCH-IMAGE` | depuración en el banco; versión con el sufijo `-bench` |

Los ganchos de inyección de fallos (NFR-WDT-01) se añaden solo a la imagen de
banco (`CONFIG_NODO_BENCH_BUILD`) y la CI ya comprueba que la de producción no
lleva su marcador.

## Comandos

```bash
# Dentro del devcontainer
. $IDF_PATH/export.sh
idf.py -B build -DSDKCONFIG=$PWD/build/sdkconfig set-target esp32s3 build      # producción
idf.py -B build-bench -DSDKCONFIG=$PWD/build-bench/sdkconfig \
  -DSDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.bench.defaults" set-target esp32s3 build
cmake -S tests/host -B build-host && cmake --build build-host && ctest --test-dir build-host   # nivel host
/opt/bench-venv/bin/python -m pytest tests/bench -m journey   # nivel bench (cuando exista el banco)
```

El flasheo y la monitorización son de `esp-idf-handling` y de los skills
`testbench-*`.
