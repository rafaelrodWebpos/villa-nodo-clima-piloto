# TC-POR-07 — Redirecciones del portal cautivo

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-a2bc8e3-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (11:30:39.347 → 11:30:51.013 UTC)
- GET http://192.168.4.1/generate_204
- GET /generate_204: 11:30:51.021 → 11:30:51.118 UTC
- GET http://192.168.4.1/hotspot-detect.html
- GET /hotspot-detect.html: 11:30:51.124 → 11:30:51.201 UTC
- log: `TC-POR-07-serie.log` (157 líneas)
- arranques del DUT (hora del banco, UTC):
  - 11:30:35.502 `rst:0x15 (USB_UART_CHIP_RESET),boot:0x8 (SPI_FAST_FLASH_BOOT)`
  - 11:30:35.502 `I (478) nodo: boot: clima-f3c6d4 fw=0.0.0-a2bc8e3-bench reset=usb part=ota_0 img=valida`
  - 11:30:38.171 `I (478) nodo: boot: clima-f3c6d4 fw=0.0.0-a2bc8e3-bench reset=usb part=ota_0 img=valida`
- /generate_204: respuesta final HTTP 200, 3510 bytes, formulario=True
- /hotspot-detect.html: respuesta final HTTP 200, 3510 bytes, formulario=True

**Resultado: PASS** — /generate_204 y /hotspot-detect.html terminan en el formulario del portal
