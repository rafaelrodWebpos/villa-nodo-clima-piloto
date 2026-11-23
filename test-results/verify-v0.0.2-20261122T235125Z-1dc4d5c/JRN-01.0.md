# JRN-01.0 — Grabar la imagen de la CI

- commit bajo prueba: `1dc4d5c43530ed6e7314c9bc0139101f5d672a28`
- imagen: `0.0.2` (variante production, run CI 45085204904)
- slot: SLOT1

- Precondiciones: slot presente

## Flasheo

- `0x0` bootloader.bin
- `0x8000` partition-table.bin
- `0x9000` nvs_blank.bin
- `0xf000` ota_data_initial.bin
- `0x20000` nodo_clima.bin

- Grabando 5 imágenes en SLOT1 (NVS en blanco)
- respuesta: ok=True returncode=0
- Wrote 21264 bytes (13674 compressed) at 0x00000000 in 0.3 seconds (571.2 kbit/s).
- Wrote 3072 bytes (128 compressed) at 0x00008000 in 0.0 seconds (725.8 kbit/s).
- Wrote 8192 bytes (31 compressed) at 0x0000f000 in 0.1 seconds (1058.8 kbit/s).
- Wrote 1083440 bytes (705962 compressed) at 0x00020000 in 5.3 seconds (1627.2 kbit/s).
- Wrote 24576 bytes (47 compressed) at 0x00009000 in 0.2 seconds (1064.1 kbit/s).

- Reset y captura del arranque: NODO-BENCH-IMAGE, Init complete

## Arranque

- log: `JRN-01.0-boot.log` (98 líneas)
- velocidad SPI de arranque: 80MHz (build: 80MHz; upstream #52, fork villa-2 20b42df o posterior)
- tras el último `rst:` (94 líneas):
- `NODO-BENCH-IMAGE`: NO
- `Init complete`: sí
- versión en el log: `I (426) nodo: nodo_clima 0.0.2`

**Resultado: PASS** — 0.0.2 arranca: sin NODO-BENCH-IMAGE + Init complete
