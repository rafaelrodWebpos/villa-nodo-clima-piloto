# TC-SEN-03 — Tres ciclos de medición con el SHT41

- imagen: `0.0.0-a6e3356-bench` (variante bench, run CI 42137497516)

- Precondiciones: grabar la imagen de la CI en SLOT1 (NVS intacta)
- Reset y observación de 3 ciclos (3 × 60 s)
- log: `TC-SEN-03-serie.log` (247 líneas)

## Resultado

- arranque: `I (449) nodo: boot: clima-f3c6d4 fw=0.0.0-a6e3356-bench reset=otro part=ota_0 img=valida`
- ts +11.2 s: `I (509) nodo: med: T=30.2 HR=71.2 Td=24.5`
- ts +14.0 s: `I (509) nodo: med: T=30.2 HR=71.2 Td=24.4`
- ts +73.9 s: `I (60509) nodo: med: T=30.2 HR=71.2 Td=24.4`
- intervalos entre líneas med: [2.7, 59.9] s (informativo; FR-MED-01 es de la Fase 2)

**Resultado: PASS** — 3 líneas med: válidas con T en [0, 50] °C
