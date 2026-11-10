# TC-POR-07 — Redirecciones del portal cautivo

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-758ccbc-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (23:26:32.234 → 23:26:43.517 UTC)
- GET http://192.168.4.1/generate_204
- GET /generate_204: 23:26:43.525 → 23:26:43.606 UTC
- GET http://192.168.4.1/hotspot-detect.html
- GET /hotspot-detect.html: 23:26:43.615 → 23:26:43.707 UTC
- log: `TC-POR-07-serie.log` (141 líneas)
- arranques del DUT (hora del banco, UTC):
  - 23:26:28.146 `rst:0x15 (USB_UART_CHIP_RESET),boot:0x8 (SPI_FAST_FLASH_BOOT)`
  - 23:26:28.146 `I (485) nodo: boot: clima-f3c6d4 fw=0.0.0-758ccbc-bench reset=usb part=ota_0 img=valida`
- /generate_204: respuesta final HTTP 200, 3510 bytes, formulario=True
- /hotspot-detect.html: respuesta final HTTP 200, 3510 bytes, formulario=True

**Resultado: PASS** — /generate_204 y /hotspot-detect.html terminan en el formulario del portal
