# TC-POR-07 — Redirecciones del portal cautivo

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-9e80669-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (10:17:03.431 → 10:17:14.076 UTC)
- GET http://192.168.4.1/generate_204
- GET /generate_204: 10:17:14.087 → 10:17:14.159 UTC
- GET http://192.168.4.1/hotspot-detect.html
- GET /hotspot-detect.html: 10:17:14.169 → 10:17:14.251 UTC
- log: `TC-POR-07-serie.log` (107 líneas)
- arranques del DUT (hora del banco, UTC):
  - 10:16:59.492 `rst:0x15 (USB_UART_CHIP_RESET),boot:0x8 (SPI_FAST_FLASH_BOOT)`
  - 10:16:59.492 `I (433) nodo: boot: clima-f3c6d4 fw=0.0.0-9e80669-bench reset=usb part=ota_0 img=valida`
- /generate_204: respuesta final HTTP 200, 3510 bytes, formulario=True
- /hotspot-detect.html: respuesta final HTTP 200, 3510 bytes, formulario=True

**Resultado: PASS** — /generate_204 y /hotspot-detect.html terminan en el formulario del portal
