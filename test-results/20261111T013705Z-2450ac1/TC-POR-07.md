# TC-POR-07 — Redirecciones del portal cautivo

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-2450ac1-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `169.254.138.107` (01:39:53.294 → 01:40:11.004 UTC)
- El banco se une al AP abierto clima-f3c6d4 (intento 2)
- sta_join intento 2: ip del banco `192.168.4.3` (01:40:13.106 → 01:40:24.255 UTC)
- GET http://192.168.4.1/generate_204
- GET /generate_204: 01:40:24.266 → 01:40:24.361 UTC
- GET http://192.168.4.1/hotspot-detect.html
- GET /hotspot-detect.html: 01:40:24.369 → 01:40:24.462 UTC
- log: `TC-POR-07-serie.log` (178 líneas)
- arranques del DUT (hora del banco, UTC):
  - 01:39:49.338 `rst:0x15 (USB_UART_CHIP_RESET),boot:0x8 (SPI_FAST_FLASH_BOOT)`
  - 01:39:49.338 `I (485) nodo: boot: clima-f3c6d4 fw=0.0.0-2450ac1-bench reset=usb part=ota_0 img=valida`
- /generate_204: respuesta final HTTP 200, 3510 bytes, formulario=True
- /hotspot-detect.html: respuesta final HTTP 200, 3510 bytes, formulario=True

**Resultado: PASS** — /generate_204 y /hotspot-detect.html terminan en el formulario del portal
