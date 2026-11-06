# Causa de reinicio de cada reset del banco (2026-11-06, imagen 0.0.0-b510420-bench)

- (A) `POST /api/serial/reset` (DTR/RTS por USB): `rst:0x15 (USB_UART_CHIP_RESET)` y la línea E1 dice `reset=usb` (FSD 0.9.4, TC-DIAG-01): el mapeo nuevo funciona en la placa.
- (B) Pulso de 0,3 s a nivel bajo en la GPIO EN del slot (17) por `POST /api/gpio/set`, luego alta impedancia: el DUT no se reinició (ninguna línea en 6 s; el pin se lee alto después). La GPIO17 del Pi no llega al EN del DUT (`gpio_wired` sin determinar), así que no se puede comprobar en este banco si un reset por EN sale como `poweron`.
- No se usó la función «Test BOOT/EN wiring» (indicación del propietario).
