# JRN-01.0 — Grabar la imagen de la CI

- commit bajo prueba: `9106b3d558faa9a8c28b32683a4647c6cb594847`
- imagen: `0.0.1` (variante production, run CI None)
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
- Wrote 21120 bytes (13588 compressed) at 0x00000000 in 0.3 seconds (565.4 kbit/s).
- Wrote 3072 bytes (128 compressed) at 0x00008000 in 0.0 seconds (749.4 kbit/s).
- Wrote 8192 bytes (31 compressed) at 0x0000f000 in 0.1 seconds (1022.4 kbit/s).
- Wrote 1079636 bytes (702791 compressed) at 0x00020000 in 5.5 seconds (1584.0 kbit/s).
- Wrote 24576 bytes (47 compressed) at 0x00009000 in 0.2 seconds (1067.4 kbit/s).

- Reset y captura del arranque: NODO-BENCH-IMAGE, Init complete

## Arranque

- log: `JRN-01.0-boot.log` (96 líneas)
- tras el último `rst:` (94 líneas):
- `NODO-BENCH-IMAGE`: NO
- `Init complete`: sí
- versión en el log: `I (504) nodo: nodo_clima 0.0.1`

**Resultado: PASS** — 0.0.1 arranca: sin NODO-BENCH-IMAGE + Init complete
