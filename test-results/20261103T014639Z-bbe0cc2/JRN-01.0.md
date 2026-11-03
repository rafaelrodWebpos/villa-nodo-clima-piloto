# JRN-01.0 — Grabar la imagen de la CI

- commit bajo prueba: `bbe0cc2b3732c08ab5336612d3067eaaf33b3cac`
- imagen: `0.0.0-bench` (variante bench, run CI 41561624338)
- slot: SLOT1

## Flasheo

- `0x0` bootloader.bin
- `0x8000` partition-table.bin
- `0x9000` nvs_blank.bin
- `0xf000` ota_data_initial.bin
- `0x20000` nodo_clima.bin

- respuesta: ok=True returncode=0

## Arranque

- log: `JRN-01.0-boot.log` (83 líneas)

- tras el último `rst:` (61 líneas):
- `NODO-BENCH-IMAGE`: sí
- `Init complete`: sí
- versión en el log: `I (274) nodo: nodo_clima 0.0.0-bench`

**Resultado: PASS** — 0.0.0-bench arranca: NODO-BENCH-IMAGE + Init complete
