# Puerta: DUT ready (cierra la Fase 2)

**Exclusión permanente:** solo artefactos commiteados y respuestas en vivo del banco. Nada de memoria, transcripciones ni relato del autor.

## Requisitos

| # | Debe ser cierto | Dónde mirar | Evidencia |
|---|---|---|---|
| 1 | Las capacidades `bench-*` están copiadas de lo que el banco reporta ahora mismo | `testing/test-plan.yaml`; `curl $TESTBENCH_URL<endpoint de reported_by>` (`$TESTBENCH_URL` en `.env`) | El endpoint de `reported_by` de cada `bench-*` en `yes` responde `ok` en vivo. Ninguna capacidad lleva el motivo «banco pendiente». Ninguna lleva ya `exercised: no`: `/commission` las ejerce o las vuelve a declarar |
| 2 | `bench-ap-internet` está resuelta (`yes` o `no` con su consecuencia), y el nivel de cada test OTA es coherente con ella (bench+ o field, FSD §22.0) | plan | Campo `tier` de los TC-OTA y JRN de OTA |
| 3 | Registro del DUT: la placa del SLOT1 es una Waveshare ESP32-S3-DEV-KIT-N8R8 (ESP32-S3, 8 MB de flash, PSRAM de 8 MB; C-HW-01/02), y el marcador de arranque aparece en la consola del slot. La parte «en ambos devnodes» de C-HW-08 no se exige aquí: se prueba en local por USB o cuando el banco tenga `bench-dual-console` | `testing/test-plan.yaml` → `dut` | `flash-id` registrado por el test de commissioning, con su commit |
| 4 | Camino de ida probado: ejecución de CI → artefacto → flasheo con los offsets de `flash_args` → marcador `Init complete` observado en serie | plan, resultado del test de camino de ida | status `successful` con commit y run id |
| 5 | La agenda de depuración no tiene abierta ninguna fila cuyo «se cierra antes de» sea DUT ready (filas 1–3) | `testing/debugging-agenda.md` | Esas filas cerradas, cada una con su capacidad pasada de `unproven` a `yes`. Las demás pueden seguir abiertas (cambio aprobado por el propietario, `testing/test-plan.yaml` → `gate_changes`) |
| 6 | No queda ninguna capacidad del proyecto en `unproven` que necesite un test de la ola 1, salvo las que cierran las filas 4–6 de la agenda (`home-assistant-test`, `reference-instrument`, `github-test-releases`). **Condición:** esas filas conservan su «se cierra antes de», y ningún test que dependa de `home-assistant-test` o `github-test-releases` puede darse por superado (`successful`) hasta que su fila de la agenda esté cerrada | plan; `testing/debugging-agenda.md` | needs × capabilities sin esas tres capacidades. Filas 4–6 de la agenda con su «se cierra antes de» intacto. Ningún test con `home-assistant-test` o `github-test-releases` en `needs` en `successful` mientras su fila siga abierta (cambio aprobado por el propietario, `gate_changes`) |
| 7 | El runner release-verify está registrado (si el propietario lo autorizó) | GitHub → Settings → Runners; `gh api repos/rafaelrodWebpos/villa-nodo-clima-piloto/actions/runners` | Runner con las etiquetas `self-hosted, testbench`; si no está, la capacidad sigue en `no` con su motivo |

## Comprobaciones mecánicas

```bash
curl -sf "$TESTBENCH_URL/api/info"
python3 -c "import yaml; p=yaml.safe_load(open('testing/test-plan.yaml')); \
  print([k for k,c in p['capabilities'].items() if c.get('reason','').startswith('banco pendiente')])"   # debe ser []
grep 'DUT ready (puerta 03)' testing/debugging-agenda.md | grep -c '| abierto'   # debe ser 0 (filas 1–3; gate_changes)
python3 -c "import yaml; p=yaml.safe_load(open('testing/test-plan.yaml')); c=p['capabilities']; \
  ex={'home-assistant-test','reference-instrument','github-test-releases'}; \
  print([(t['id'],n) for t in p['tests'] if t.get('wave')==1 for n in t.get('needs',[]) if c.get(n,{}).get('available')=='unproven' and n not in ex])"   # debe ser []
python3 -c "import yaml; p=yaml.safe_load(open('testing/test-plan.yaml')); c=p['capabilities']; \
  print([t['id'] for t in p['tests'] if t.get('status')=='successful' and any(c.get(n,{}).get('available')!=True for n in t.get('needs',[]) if n in ('home-assistant-test','github-test-releases'))])"   # debe ser [] (condición de la fila 6)
```

## Trampas de este proyecto

- Un USB nativo abierto con DTR/RTS activos detiene el S3 y parece un cuelgue (testing.md).
- Leer el tamaño de flash del log del bootloader: repite la configuración, no mide el chip.
- Dar por buena la salida a Internet del AP porque «el banco suele tenerla».

## Veredicto
`OPEN` · `SHUT` + hallazgos.
