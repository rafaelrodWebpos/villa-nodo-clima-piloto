# Puertas — Nodo Clima Piloto

Un fichero por puerta. Cada una la evalúa un **checker nuevo** (un subagente que
no hizo el trabajo y no ha visto la conversación) con dos entradas: el fichero
de la puerta y el repositorio.

**Exclusión permanente:** la evidencia son solo los artefactos commiteados y
las respuestas en vivo del banco o de GitHub. Nunca la memoria del asistente,
transcripciones, notas de decisiones ni el relato del autor. Lo que no está en
el repositorio no existe.

**Veredicto:** `OPEN`, o `SHUT` con cada hallazgo (requisito, evidencia buscada,
lo que se encontró). El checker no arregla nada. Si la puerta está `SHUT`, el
autor vuelve al paso que corresponde a cada hallazgo y un checker **nuevo**
repite la puerta entera. El veredicto se anota en `testing/test-plan.yaml` →
`gate_verdicts`, con su fecha y su commit.

| Fichero | Puerta | Cierra |
|---|---|---|
| `01-load-defined.md` | Load defined | Fase 0 · Definición |
| `02-ai-harnessed.md` | AI harnessed | Fase 1 · Harness |
| `03-dut-ready.md` | DUT ready | Fase 2 · Commissioning |
| `04-ready-for-shipment.md` | Ready for shipment | Fase 3 · Build |
| `05-shipped.md` | Shipped | Release |
