# TC-POR-07 — Redirecciones del portal cautivo

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-b2fffa7-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (15:44:59.895 → 15:45:12.536 UTC)
- GET http://192.168.4.1/generate_204
- GET /generate_204: 15:45:12.546 → 15:45:12.630 UTC
- GET http://192.168.4.1/hotspot-detect.html
- GET /hotspot-detect.html: 15:45:12.640 → 15:45:12.710 UTC
- log: `TC-POR-07-serie.log` (107 líneas)
- arranques del DUT (hora del banco, UTC):
  - 15:44:56.281 `rst:0x15 (USB_UART_CHIP_RESET),boot:0x8 (SPI_FAST_FLASH_BOOT)`
  - 15:44:56.281 `I (513) nodo: boot: clima-f3c6d4 fw=0.0.0-b2fffa7-bench reset=usb part=ota_0 img=valida`
- /generate_204: respuesta final HTTP 200, 3510 bytes, formulario=True
- /hotspot-detect.html: respuesta final HTTP 200, 3510 bytes, formulario=True

**Resultado: PASS** — /generate_204 y /hotspot-detect.html terminan en el formulario del portal
