# Puerta: AI harnessed (cierra la Fase 1)

**Exclusión permanente:** solo artefactos commiteados y respuestas en vivo de GitHub y del banco. Nada de memoria, transcripciones ni relato del autor.

El banco se consulta en `$TESTBENCH_URL`, que está en `.env`. Ese fichero lo ignora git porque el repo es público. Solo se hacen lecturas GET y nunca se toca el DUT: la Fase 1 no lo flashea, ni lo reinicia, ni lo lee.

Repositorio: `rafaelrodWebpos/villa-nodo-clima-piloto`. Plan: `testing/test-plan.yaml`. FSD: `docs/Functionality/FSD-nodo-clima.md`.

## Requisitos

| # | Debe ser cierto | Dónde mirar | Evidencia |
|---|---|---|---|
| 1 | La puerta Load defined sigue abierta para la versión actual del FSD | `01-load-defined.md` | Sus comprobaciones mecánicas pasan |
| 2 | El plan declara capacidades. Cada `bench-*` en `yes` lleva un `reported_by` con el endpoint del banco que la respalda. Cada `bench-*` en `no` lleva su motivo y ninguna dice «banco pendiente». Las del proyecto están en `unproven`, salvo `hosted-ci` | `testing/test-plan.yaml` → `capabilities`; `curl $TESTBENCH_URL/api/…` | El endpoint de cada `reported_by` responde `ok` en vivo. Ninguna capacidad de proyecto tiene `observed:` |
| 3 | El journey está sembrado: `JRN-01.0`…`JRN-01.7` (grabar el artefacto de la CI → portal → aprovisionar → Wi-Fi → broker/status → HA → dos medidas con ts → corte de alimentación) y `JRN-02.*` (OTA y rollback, bench+), cada uno con `verifies` (IDs que existen en el FSD), `needs` (capacidades declaradas), `expect`, `kind: standard`, `wave: 1` | `testing/test-plan.yaml` → `tests` | Pasos consecutivos. Ningún paso de OTA dentro de JRN-01 |
| 4 | Existe la agenda de depuración y cada punto tiene «sin probar porque» y «se prueba con»; el testbench no figura como punto | `testing/debugging-agenda.md` | Tabla |
| 5 | Existe el estándar de pruebas, en un solo fichero, con reglas de ejecución y procedimientos compartidos | `docs/Method/standards/testing.md` | Secciones «Reglas para cualquier ejecución» y `P-*` |
| 6 | El firmware es un esqueleto: no hay ningún módulo que el FSD no pida y ningún requisito implementado | `main/`, `components/` | Solo `main/main.c` con el log de versión, el marcador de banco y `Init complete`; sin `components/` |
| 7 | Las restricciones de build del FSD están en la configuración | `sdkconfig.defaults`, `partitions.csv` | Flash de 8 MB; tabla idéntica a FSD §2.2; PSRAM no activada; `CONFIG_NODO_UDP_LOG` no activado |
| 8 | La CI tiene build en cada push, release por tag y un job verify del que depende la release | `.github/workflows/build.yml` | `release.needs` contiene `verify`; verify solo con `refs/tags/v` |
| 9 | La CI ha pasado en verde al menos una vez en `main` | GitHub | `gh run list` |
| 10 | El devcontainer construye y contiene el runner sin registrar; el registro está documentado como autorización del propietario | `.devcontainer/`, `scripts/runner/register.sh`, workflow `devcontainer image builds` | Ejecución verde; el script no se ejecuta solo |
| 11 | Las 5 puertas existen y son específicas de este proyecto | `testing/gates/` | Rutas e IDs de este repo, no genéricos |

## Comprobaciones mecánicas

```bash
test -f testing/test-plan.yaml && test -f testing/debugging-agenda.md
ls .github/workflows/build.yml .github/workflows/ci.yml
python3 -c "import yaml,sys; p=yaml.safe_load(open('testing/test-plan.yaml')); \
  j=[t for t in p['tests'] if t['id'].startswith('JRN-')]; \
  caps=p['capabilities']; \
  bad=[k for k,c in caps.items() if k.startswith('bench-') and c['available'] is True and not c.get('reported_by')]; \
  pend=[k for k,c in caps.items() if 'banco pendiente' in str(c.get('reason',''))]; \
  undef=[(t['id'],n) for t in p['tests'] for n in t['needs'] if n not in caps]; \
  print('journey',len(j),'yes-sin-reporte',bad,'pendiente',pend,'needs-sin-capacidad',undef); \
  sys.exit(0 if j and not bad and not pend and not undef else 1)"
# YAML lee `yes` como booleano: compara con True, no con 'yes'
grep -oP '(?<![A-Z])((FR|NFR|C)-[A-Z]+-[0-9]+|T[0-9]{2})(?![0-9])' testing/test-plan.yaml | sort -u | \
  while read id; do grep -q -- "$id" docs/Functionality/FSD-nodo-clima.md || echo "ID no está en el FSD: $id"; done
set -a; . ./.env; set +a
for e in /api/info /api/devices /api/udplog /api/wifi/ap_status /api/wifi/events /api/mqtt/status /api/human/status; do \
  curl -s -m 5 "$TESTBENCH_URL$e" | grep -q '"ok": true' && echo "ok $e" || echo "FALLA $e"; done
test ! -d components
grep -q 'CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y' sdkconfig.defaults
! grep -q '^CONFIG_NODO_UDP_LOG=y' sdkconfig.defaults
gh run list -R rafaelrodWebpos/villa-nodo-clima-piloto -b main -L 10 --json workflowName,conclusion \
  --jq '[.[]|select(.conclusion=="success")|.workflowName]|unique'
#   debe incluir: "Build Firmware", "host tests + secret scan", "devcontainer image builds"
```

## Comprobación de comportamiento (la que decide)

Abre una sesión `/build` con solo el repositorio. ¿Puede decir, sin preguntar
nada: la fase (2 · Commissioning, porque la agenda tiene puntos abiertos), el
siguiente punto de la agenda y cómo probarlo? Si tiene que preguntar algo, la
información que le falta es el hallazgo.

## Trampas de este proyecto

- Capacidades del banco en `yes` copiadas de la documentación del testbench, sin un endpoint del banco que las reporte. Ejemplos: salida a Internet, bloqueo de SNTP, DNS propio, corte de alimentación, autenticación del broker.
- La dirección IP del banco escrita en un fichero versionado. Solo puede estar en `.env`.
- Evidencia del tipo `observed:` que solo podría venir de la placa: la Fase 1 no toca el DUT.
- El log UDP activado en la configuración de producción (choca con C-LOG-01).
- El patrón `build/` del `.gitignore` excluyendo `.claude/skills/build/` (ya pasó).
- El job verify con un trigger de pull request (repositorio público + runner self-hosted).

## Veredicto
`OPEN` · `SHUT` + hallazgos.
