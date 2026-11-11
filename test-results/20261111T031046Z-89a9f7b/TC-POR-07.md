# TC-POR-07 — Redirecciones del portal cautivo

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-89a9f7b-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (03:13:10.415 → 03:13:20.538 UTC)
- GET http://192.168.4.1/generate_204
- GET /generate_204: 03:13:20.548 → 03:13:20.638 UTC
- GET http://192.168.4.1/hotspot-detect.html
- GET /hotspot-detect.html: 03:13:20.646 → 03:13:20.746 UTC
- log: `TC-POR-07-serie.log` (144 líneas)
- arranques del DUT (hora del banco, UTC):
  - 03:13:06.543 `rst:0x15 (USB_UART_CHIP_RESET),boot:0x8 (SPI_FAST_FLASH_BOOT)`
  - 03:13:06.543 `I (486) nodo: boot: clima-f3c6d4 fw=0.0.0-89a9f7b-bench reset=usb part=ota_0 img=valida`
- /generate_204: respuesta final HTTP 200, 3510 bytes, formulario=True
- /hotspot-detect.html: respuesta final HTTP 200, 3510 bytes, formulario=True

**Resultado: PASS** — /generate_204 y /hotspot-detect.html terminan en el formulario del portal
