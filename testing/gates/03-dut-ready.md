# Puerta: DUT ready (cierra la Fase 2)

**Exclusión permanente:** solo artefactos commiteados y respuestas en vivo del banco. Nada de memoria, transcripciones ni relato del autor.

## Requisitos

| # | Debe ser cierto | Dónde mirar | Evidencia |
|---|---|---|---|
| 1 | Las capacidades `bench-*` están copiadas de lo que el banco reporta ahora mismo | `testing/test-plan.yaml`; `curl $TESTBENCH_URL/api/info` | Cada `bench-*` en `yes` aparece en la respuesta en vivo; ninguna sigue con el motivo «banco pendiente» |
| 2 | `bench-ap-internet` está resuelta (`yes` o `no` con su consecuencia), y el nivel de cada test OTA es coherente con ella (bench+ o field, FSD §22.0) | plan | Campo `tier` de los TC-OTA y JRN de OTA |
| 3 | Registro del DUT: la placa es una DevKitC-1 N8R8 con 8 MB de flash (C-HW-01/02), con el slot asignado | `testing/test-plan.yaml` → `dut` | `flash-id` registrado por el test de commissioning, con su commit |
| 4 | Camino de ida probado: ejecución de CI → artefacto → flasheo con los offsets de `flash_args` → marcador `Init complete` observado en serie | plan, resultado del test de camino de ida | status `successful` con commit y run id |
| 5 | La agenda de depuración no tiene puntos abiertos del lado del proyecto | `testing/debugging-agenda.md` | Todas las filas cerradas, cada una con su capacidad pasada de `unproven` a `yes` |
| 6 | No queda ninguna capacidad del proyecto en `unproven` que necesite un test de la ola 1 | plan | needs × capabilities |
| 7 | El runner release-verify está registrado (si el propietario lo autorizó) | GitHub → Settings → Runners; `gh api repos/rafaelrodWebpos/villa-nodo-clima-piloto/actions/runners` | Runner con las etiquetas `self-hosted, testbench`; si no está, la capacidad sigue en `no` con su motivo |

## Comprobaciones mecánicas

```bash
curl -sf "$TESTBENCH_URL/api/info"
python3 -c "import yaml; p=yaml.safe_load(open('testing/test-plan.yaml')); \
  print([k for k,c in p['capabilities'].items() if c.get('reason','').startswith('banco pendiente')])"   # debe ser []
grep -c '| abierto' testing/debugging-agenda.md   # debe ser 0
```

## Trampas de este proyecto

- Un USB nativo abierto con DTR/RTS activos detiene el S3 y parece un cuelgue (testing.md).
- Leer el tamaño de flash del log del bootloader: repite la configuración, no mide el chip.
- Dar por buena la salida a Internet del AP porque «el banco suele tenerla».

## Veredicto
`OPEN` · `SHUT` + hallazgos.
