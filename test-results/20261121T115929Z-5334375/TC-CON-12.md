# TC-CON-12 — Broker parado 60 min

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1

**Resultado: FAIL** — AssertionError: el AP del banco está activo: no es nuestro, no se toca
