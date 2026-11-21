# TC-HW-03 — Arranque sin PSRAM

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)

- Precondiciones: grabar la imagen de la CI en SLOT1
- Reset y 120 s de observación
- log: `TC-HW-03-serie.log` (214 líneas)

## Resultado

- fin_arranque: `I (623) nodo: con: ARRANQUE -> CONECTANDO_WIFI (fin_arranque)`
- líneas E1: 1
- Guru Meditation / abort(): 0

**Resultado: PASS** — fin_arranque sin PSRAM, sin abortar y con un solo arranque en 120 s
