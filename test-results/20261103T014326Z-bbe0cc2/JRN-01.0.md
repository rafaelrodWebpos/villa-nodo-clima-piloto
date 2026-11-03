# JRN-01.0 — Grabar la imagen de la CI

- commit bajo prueba: `bbe0cc2b3732c08ab5336612d3067eaaf33b3cac`
- imagen: `0.0.0` (variante production, run CI 41561334943)
- slot: SLOT1

## Flasheo

- `0x0` bootloader.bin
- `0x8000` partition-table.bin
- `0x9000` nvs_blank.bin
- `0xf000` ota_data_initial.bin
- `0x20000` nodo_clima.bin

- respuesta: ok=True returncode=0

## Arranque

- log: `JRN-01.0-boot.log` (81 líneas)

- tras el último `rst:` (60 líneas):
- `NODO-BENCH-IMAGE`: NO
- `Init complete`: sí
- versión en el log: `I (273) nodo: nodo_clima 0.0.0`

**Resultado: PASS** — 0.0.0 arranca: sin NODO-BENCH-IMAGE + Init complete
