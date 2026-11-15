# JRN-01.0 — Grabar la imagen de la CI

- commit bajo prueba: `cfb249a8bd7a40f426832145b1552fdba7fa4a72`
- imagen: `0.0.0-cfb249a` (variante production, run CI None)
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

- Reset y captura del arranque: NODO-BENCH-IMAGE, Init complete

## Arranque

- log: `JRN-01.0-boot.log` (96 líneas)
- tras el último `rst:` (94 líneas):
- `NODO-BENCH-IMAGE`: NO
- `Init complete`: sí
- versión en el log: `I (505) nodo: nodo_clima 0.0.0-cfb249a`

**Resultado: PASS** — 0.0.0-cfb249a arranca: sin NODO-BENCH-IMAGE + Init complete
