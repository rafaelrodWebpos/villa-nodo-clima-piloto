# TC-SEN-03 — Tres ciclos de medición con el SHT41

- imagen: `0.0.0-bench` (variante bench, run CI 42133220878)

- Precondiciones: grabar la imagen de la CI en SLOT1 (NVS intacta)
- Reset y observación de 3 ciclos (3 × 60 s)
- log: `TC-SEN-03-serie.log` (251 líneas)

## Resultado

- arranque: `I (448) nodo: boot: clima-f3c6d4 fw=0.0.0-bench reset=otro part=ota_0 img=valida`
- ts +11.2 s: `I (508) nodo: med: T=30.0 HR=72.2 Td=24.4`
- ts +13.9 s: `I (508) nodo: med: T=30.0 HR=72.1 Td=24.4`
- ts +73.9 s: `I (60508) nodo: med: T=30.0 HR=72.0 Td=24.4`
- intervalos entre líneas med: [2.8, 59.9] s (informativo; FR-MED-01 es de la Fase 2)

**Resultado: PASS** — 3 líneas med: válidas con T en [0, 50] °C
