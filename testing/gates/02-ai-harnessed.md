# Puerta: AI harnessed (cierra la Fase 1)

**Exclusión permanente:** solo artefactos commiteados y respuestas en vivo de GitHub. Nada de memoria, transcripciones ni relato del autor.

Repositorio: `rafaelrodWebpos/villa-nodo-clima-piloto`. Plan: `testing/test-plan.yaml`. FSD: `docs/Functionality/FSD-nodo-clima.md`.

## Requisitos

| # | Debe ser cierto | Dónde mirar | Evidencia |
|---|---|---|---|
| 1 | La puerta Load defined sigue abierta para la versión actual del FSD | `01-load-defined.md` | Sus comprobaciones mecánicas pasan |
| 2 | El plan declara capacidades: las del banco como `available: no` con el motivo «banco pendiente» (el banco no existe) y las del proyecto como `unproven` o `yes` | `testing/test-plan.yaml` → `capabilities` | Ninguna capacidad del banco en `yes` sin una respuesta del banco que la respalde |
| 3 | El journey está sembrado: tests `JRN-01.<paso>`, uno por paso, cada uno con `verifies`, `needs`, `expect`, `kind: standard`, `wave: 1` | `testing/test-plan.yaml` → `tests` | Al menos un `JRN-01.*` y pasos consecutivos |
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
  bad=[k for k,c in p['capabilities'].items() if k.startswith('bench-') and c['available']=='yes']; \
  print('journey',len(j),'bench-yes',bad); sys.exit(0 if j and not bad else 1)"
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

- Capacidades del banco en `yes` copiadas de la documentación del testbench, sin un banco que las reporte. El banco no existe.
- Evidencia del tipo `observed:` que solo podría venir de la placa: la Fase 1 no toca el DUT.
- El log UDP activado en la configuración de producción (choca con C-LOG-01).
- El patrón `build/` del `.gitignore` excluyendo `.claude/skills/build/` (ya pasó).
- El job verify con un trigger de pull request (repositorio público + runner self-hosted).

## Veredicto
`OPEN` · `SHUT` + hallazgos.
