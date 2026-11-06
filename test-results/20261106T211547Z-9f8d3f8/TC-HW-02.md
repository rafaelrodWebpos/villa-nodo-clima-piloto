# TC-HW-02 — Lectura del chip y de la flash

- Precondiciones: SLOT1 presente
- POST /api/chip/info (esptool en el Pi; la placa se reinicia sola)
- log: `TC-HW-02-esptool.log` (24 líneas)

## Resultado

- chip: `ESP32-S3 (QFN56)` v0.2
- features: `Wi-Fi, BT 5 (LE), Dual Core + LP Core, 240MHz, Embedded PSRAM 8MB (AP_3v3)`
- flash: `8MB`
- USB del slot: ['1a86:55d3', '303a:1001']

**Resultado: PASS** — ESP32-S3 con PSRAM de 8 MB, flash de 8 MB y las dos interfaces del único USB-C
