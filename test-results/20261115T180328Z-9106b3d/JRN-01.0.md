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

- Reset y captura del arranque: NODO-BENCH-IMAGE, Init complete

## Arranque

- log: `JRN-01.0-boot.log` (741 líneas)
- tras el último `rst:` (38 líneas):
- `NODO-BENCH-IMAGE`: NO
- `Init complete`: NO
- versión en el log: ``

**Resultado: FAIL** — AssertionError: «Init complete» no aparece en el arranque
assert False
