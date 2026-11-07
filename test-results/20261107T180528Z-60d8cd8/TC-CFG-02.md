# TC-CFG-02 — Cinco cortes de alimentación

- imagen: `0.0.0-60d8cd8-bench` (variante bench, run CI 42399261163)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1

**Resultado: FAIL** — AssertionError: flash falló: esptool exited 2
assert (False)
 +  where False = <built-in method get of dict object at 0x7851edb79680>('ok')
 +    where <built-in method get of dict object at 0x7851edb79680> = {'error': 'esptool exited 2', 'ok': False, 'output': "esptool v5.6.0\nSerial port /dev/ttyACM0:\n\nERROR: A fatal erro...o 11] Could not exclusively lock port /dev/ttyACM0: [Errno 11] Resource temporarily unavailable)\n\n", 'returncode': 2}.get
