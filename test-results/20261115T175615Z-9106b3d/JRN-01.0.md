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
- respuesta: ok=False returncode=2


**Resultado: FAIL** — AssertionError: flash falló: esptool exited 2
assert (False)
 +  where False = <built-in method get of dict object at 0x7be26fe15d80>('ok')
 +    where <built-in method get of dict object at 0x7be26fe15d80> = {'error': 'esptool exited 2', 'ok': False, 'output': 'esptool v5.6.0\nSerial port /dev/ttyACM1:\nConnecting....\nConne...leshooting steps visit: https://docs.espressif.com/projects/esptool/en/latest/troubleshooting.html\n', 'returncode': 2}.get
