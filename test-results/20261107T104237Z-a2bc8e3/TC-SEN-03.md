# TC-SEN-03 — Tres ciclos de medición con el SHT41

- imagen: `0.0.0-a2bc8e3-bench` (variante bench, run CI 42365108439)

- Precondiciones: grabar la imagen de la CI en SLOT1 (NVS intacta)
- Reset y observación de 3 ciclos (3 × 60 s)
- log: `TC-SEN-03-serie.log` (284 líneas)

## Resultado

- arranque: `I (478) nodo: boot: clima-f3c6d4 fw=0.0.0-a2bc8e3-bench reset=usb part=ota_0 img=valida`
- ts +11.0 s: `I (538) nodo: med: T=28.7 HR=69.1 Td=22.5`
- ts +13.8 s: `I (538) nodo: med: T=28.7 HR=70.2 Td=22.8`
- ts +73.8 s: `I (60538) nodo: med: T=28.7 HR=69.9 Td=22.7`
- intervalos entre líneas med: [2.8, 59.9] s (informativo; FR-MED-01 es de la Fase 2)

**Resultado: PASS** — 3 líneas med: válidas con T en [0, 50] °C
