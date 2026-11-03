# JRN-01.0 — Grabar la imagen de la CI

- commit bajo prueba: `c1ce488a070d11eed0570b1f1487211290795e2b`
- imagen: `0.0.0-bench` (variante bench, run CI 41557361297)
- slot: SLOT1

## Flasheo

- `0x0` bootloader.bin
- `0x8000` partition-table.bin
- `0x9000` nvs_blank.bin
- `0xf000` ota_data_initial.bin
- `0x20000` nodo_clima.bin

**Resultado: FAIL** — 
