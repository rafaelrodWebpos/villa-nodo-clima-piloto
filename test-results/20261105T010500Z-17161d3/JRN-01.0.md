# JRN-01.0 — Grabar la imagen de la CI

- commit bajo prueba: `17161d32a602350865706de521bc196f22658c60`
- imagen: `0.0.0-bench` (variante bench, run CI 41945683891)
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

- log: `JRN-01.0-boot.log` (98 líneas)
- tras el último `rst:` (94 líneas):
- `NODO-BENCH-IMAGE`: sí
- `Init complete`: sí
- versión en el log: `I (438) nodo: nodo_clima 0.0.0-bench`

**Resultado: PASS** — 0.0.0-bench arranca: NODO-BENCH-IMAGE + Init complete
