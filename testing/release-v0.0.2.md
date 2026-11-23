# Release v0.0.2: comprobaciones de §19.3 (2026-11-22)

- **SEC-01** (comprobado por Claude a petición del propietario): la aprobación de workflows es
  `all_external_contributors` y no había ningún runner registrado antes de la release.
- **SEC-15**, avisos de Espressif publicados desde el 2026-10-20, frente a `main/idf_component.yml`,
  `dependencies.lock` (solo `idf` 6.0.3 y `espressif/mqtt` 1.1.0) y el `sdkconfig` de la imagen de producción
  (`9e80669`, idéntico en firmware al tag):

| Aviso | Componente | ¿Aplica? | Motivo |
|---|---|---|---|
| GHSA-6rwr-fjg5-hh5j (2026-11-19), DoS en el parser DNS | `esp_dns` (esp-protocols) | No | No está en las dependencias ni en el código. El DNS es el de lwIP |
| GHSA-7fpr-vjw5-2c86 (2026-10-30), recursión en mDNS | `espressif/mdns` | No | No está en las dependencias. `CONFIG_LWIP_DNS_SUPPORT_MDNS_QUERIES=y` es el resolvedor de lwIP (valor por defecto), no ese componente |
| GHSA-2j6m-56jw-9mqg (2026-10-29), `esp_modem` | `espressif/esp_modem` | No | No está en las dependencias |
| GHSA-rjvf-fxv5-x87j (2026-11-02), BLE Mesh | ESP-BLE-MESH | No | `# CONFIG_BT_ENABLED is not set` |
| GHSA-c26h-gm53-qg83 (2026-10-30), Thread Border Router | OpenThread BR | No | `# CONFIG_OPENTHREAD_ENABLED is not set` |
| GHSA-49x8-xqjg-2pjg (2026-10-27), ESP-TEE | `esp_tee` | No | No está configurado (ningún `CONFIG_SECURE_ENABLE_TEE` en el `sdkconfig`) |
| GHSA-ch63-jxm5-vmvf (2026-10-30), caché DNS de lwIP | lwIP DNS | Corregido | ESP-IDF 6.0.3, y además `CONFIG_LWIP_DNS_MAX_HOST_IP=1` (`build_checks`) |

En el código (`main/`, `components/`) no hay ninguna referencia a `esp_dns`, `mdns`, `esp_modem`, `esp_tee`, BLE
Mesh, NimBLE, Bluedroid ni OpenThread.

## Release (2026-11-22)

- **Tag** `v0.0.2` sobre `1dc4d5c`; ejecución de Build Firmware 45085204904: build, verify y release en verde.
- **Release publicada:** `firmware_v0.0.2.bin` y `firmware_v0.0.2.elf`, no es pre-release.
- **Journey de verify** (imagen de producción `0.0.2`, `test-results/verify-v0.0.2-20261122T235125Z-1dc4d5c/`):
  - JRN-01.0 a 01.4 en verde;
  - JRN-01.5 not done (no hay Home Assistant de prueba en el workspace del runner);
  - **JRN-01.7 en verde:** el banco vio el SLOT1 ausente 0,5 s después del aviso de desenchufar y enchufado otra
    vez a los 85 s; primer status con `reset=poweron` y `uptime_s=1`. El propietario dice que no vio el aviso.
    Queda por aclarar quién hizo ese corte.
- **TC-OTA-14 (FR-OTA-13)** en verde (`test-results/verify-v0.0.2-20261123T000026Z-1dc4d5c/`): `rechazado:ruta`
  a 0,22 s, sin pasar a OTA_DESCARGA.
- **Runner:** levantado solo durante la release; al terminar no quedó ninguno registrado.
