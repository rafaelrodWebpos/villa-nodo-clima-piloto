# TC-POR-07 — Redirecciones del portal cautivo

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-a2bc8e3-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (11:30:06.630 → 11:30:18.862 UTC)
- GET http://192.168.4.1/generate_204
- GET /generate_204: 11:30:18.871 → 11:30:18.963 UTC
- GET http://192.168.4.1/hotspot-detect.html
- GET /hotspot-detect.html: 11:30:18.972 → 11:30:19.090 UTC
- log: `TC-POR-07-serie.log` (152 líneas)
- arranques del DUT (hora del banco, UTC):
  - 11:30:02.787 `rst:0x15 (USB_UART_CHIP_RESET),boot:0x8 (SPI_FAST_FLASH_BOOT)`
  - 11:30:02.787 `I (478) nodo: boot: clima-f3c6d4 fw=0.0.0-a2bc8e3-bench reset=usb part=ota_0 img=valida`
  - 11:30:05.434 `I (478) nodo: boot: clima-f3c6d4 fw=0.0.0-a2bc8e3-bench reset=usb part=ota_0 img=valida`
- /generate_204: respuesta final HTTP 200, 3510 bytes, formulario=True
- /hotspot-detect.html: respuesta final HTTP 200, 3510 bytes, formulario=True

**Resultado: PASS** — /generate_204 y /hotspot-detect.html terminan en el formulario del portal
