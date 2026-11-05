# Puerta: AI harnessed (cierra la Fase 1)

**Exclusión permanente:** solo artefactos commiteados y respuestas en vivo de GitHub y del banco. Nada de memoria, transcripciones ni relato del autor.

El banco se consulta en `$TESTBENCH_URL`, que está en `.env`. Ese fichero lo ignora git porque el repo es público. Solo se hacen lecturas GET y nunca se toca el DUT: la Fase 1 no lo flashea, ni lo reinicia, ni lo lee.

Repositorio: `rafaelrodWebpos/villa-nodo-clima-piloto`. Plan: `testing/test-plan.yaml`. FSD: `docs/Functionality/FSD-nodo-clima.md`.

## Requisitos

| # | Debe ser cierto | Dónde mirar | Evidencia |
|---|---|---|---|
| 1 | La puerta Load defined sigue abierta para la versión actual del FSD | `01-load-defined.md` | Sus comprobaciones mecánicas pasan |
| 2 | El plan declara capacidades. Cada `bench-*` del banco en `yes` lleva un `reported_by` con el endpoint del banco que la respalda. Cada `bench-*` en `no` lleva su motivo y ninguna dice «banco pendiente». `bench-driver` es una instalación del proyecto, no del banco: está en `no` con su motivo, o en `yes` con `pinned` y con `installed_by.run` = un run verde de «devcontainer image builds» cuya comprobación importa TestbenchDriver y lee el commit fijado. Las del proyecto están en `unproven`, salvo `hosted-ci` (`yes`), `release-verification` (`no` con su motivo) y las que ya observó el commissioning: esas pueden estar en `yes` con un `observed:` que cita un commit, solo si la puerta 03 consta `OPEN` en `gate_verdicts`. Cada `exercised: no` dice qué fase lo ejerce | `testing/test-plan.yaml` → `capabilities`, `gate_verdicts`; `curl $TESTBENCH_URL/api/…`; `gh run view` | El endpoint de cada `reported_by` responde `ok` en vivo. El run de `installed_by.run` es `success` y su log contiene `TestbenchDriver OK` y el commit de `pinned`. Ninguna capacidad de proyecto tiene `observed:` sin commit, ni antes de que la puerta 03 conste `OPEN` |
| 3 | El journey está sembrado: `JRN-01.0`…`JRN-01.7` (grabar el artefacto de la CI → portal → aprovisionar → Wi-Fi → broker/status → HA → dos medidas con ts → corte de alimentación) y `JRN-02.*` (OTA y rollback, bench+), cada uno con `verifies` (IDs que existen en el FSD), `needs` (capacidades declaradas), `expect`, `kind: standard`, `wave: 1` | `testing/test-plan.yaml` → `tests` | Pasos consecutivos. Ningún paso de OTA dentro de JRN-01 |
| 4 | Existe la agenda de depuración y cada punto tiene «sin probar porque» y «se prueba con»; el testbench no figura como punto | `testing/debugging-agenda.md` | Tabla |
| 5 | Existe el estándar de pruebas, en un solo fichero, con reglas de ejecución y procedimientos compartidos | `docs/Method/standards/testing.md` | Secciones «Reglas para cualquier ejecución» y `P-*` |
| 6 | No hay código que el FSD no pida. Mientras la puerta 03 no conste `OPEN` en `gate_verdicts`, el firmware es un esqueleto: ningún módulo que el FSD no pida y ningún requisito implementado. Cuando la puerta 03 consta `OPEN`, cada componente de `components/` corresponde a requisitos del FSD con tests declarados en el plan: cita al menos un ID, todos los IDs que cita existen en el FSD y cada uno está en el `verifies` de algún test del plan | `main/`, `components/`, `testing/test-plan.yaml` → `gate_verdicts`, `tests` | Antes de la puerta 03: solo `main/main.c` con el log de versión, el marcador de banco y `Init complete`; sin `components/`. Después: ningún componente sin IDs, con un ID que no está en el FSD o con un ID sin test declarado |
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
  bad=[k for k,c in caps.items() if k.startswith('bench-') and k!='bench-driver' and c['available'] is True and not c.get('reported_by')]; \
  d=caps['bench-driver']; drv=[] if d['available'] is not True else [x for x in ('pinned','installed_by') if not d.get(x)]+([] if (d.get('installed_by') or {}).get('run') else ['installed_by.run']); \
  g3=any(v['gate']=='03-dut-ready' and v['verdict']=='OPEN' for v in p.get('gate_verdicts',[])); \
  import re; obs=[k for k,c in caps.items() if not k.startswith('bench-') and c.get('observed') and not (g3 and re.search(r'\\b[0-9a-f]{7,40}\\b',str(c['observed'])))]; \
  pend=[k for k,c in caps.items() if 'banco pendiente' in str(c.get('reason',''))]; \
  undef=[(t['id'],n) for t in p['tests'] for n in t['needs'] if n not in caps]; \
  print('journey',len(j),'yes-sin-reporte',bad,'pendiente',pend,'needs-sin-capacidad',undef,'bench-driver-falta',drv,'observed-sin-commit-o-sin-puerta03',obs); \
  sys.exit(0 if j and not bad and not pend and not undef and not drv and not obs else 1)"
# YAML lee `yes` como booleano: compara con True, no con 'yes'
# bench-driver en yes: su run de installed_by es verde y prueba el import y el commit fijado
python3 -c "import yaml; d=yaml.safe_load(open('testing/test-plan.yaml'))['capabilities']['bench-driver']; print(d['installed_by']['run'], d['pinned'])" | { read run pin; \
  test "$(gh run view "$run" -R rafaelrodWebpos/villa-nodo-clima-piloto --json conclusion,workflowName --jq '.workflowName+" "+.conclusion')" = "devcontainer image builds success" && \
  log=$(gh run view "$run" -R rafaelrodWebpos/villa-nodo-clima-piloto --json jobs --jq '.jobs[].databaseId' | \
    while read j; do gh api "repos/rafaelrodWebpos/villa-nodo-clima-piloto/actions/jobs/$j/logs"; done) && \
  printf '%s' "$log" | grep -q 'TestbenchDriver OK' && \
  printf '%s' "$log" | grep -q "$pin" && echo "bench-driver ok ($run)" || echo "FALLA bench-driver ($run)"; }
# el log se lee por la API de jobs: «gh run view --log» sale vacío con gh 2.46
grep -oP '(?<![A-Z])((FR|NFR|C)-[A-Z]+-[0-9]+|T[0-9]{2})(?![0-9])' testing/test-plan.yaml | sort -u | \
  while read id; do grep -q -- "$id" docs/Functionality/FSD-nodo-clima.md || echo "ID no está en el FSD: $id"; done
set -a; . ./.env; set +a
for e in /api/info /api/devices /api/udplog /api/wifi/ap_status /api/wifi/events /api/mqtt/status /api/human/status; do \
  curl -s -m 5 "$TESTBENCH_URL$e" | grep -q '"ok": true' && echo "ok $e" || echo "FALLA $e"; done
# fila 6: esqueleto antes de la puerta 03; después, cada componente con IDs del FSD y tests declarados
python3 -c "import yaml,re,sys,pathlib; p=yaml.safe_load(open('testing/test-plan.yaml')); \
  g3=any(v['gate']=='03-dut-ready' and v['verdict']=='OPEN' for v in p.get('gate_verdicts',[])); \
  c=pathlib.Path('components'); \
  sys.exit(0 if not c.exists() else 1) if not g3 else None; \
  fsd=open('docs/Functionality/FSD-nodo-clima.md').read(); ver={v for t in p['tests'] for v in t.get('verifies',[])}; \
  rx=re.compile(r'(?<![A-Z])((?:FR|NFR|C)-[A-Z]+-[0-9]+|T[0-9]{2})(?![0-9])'); mal=[]; \
  [mal.append((d.name, 'sin IDs' if not ids else sorted(i for i in ids if i not in fsd or i not in ver))) \
   for d in sorted(c.iterdir()) if d.is_dir() \
   for ids in [set(x for f in d.rglob('*') if f.is_file() for x in rx.findall(f.read_text(errors='ignore')))] \
   if not ids or any(i not in fsd or i not in ver for i in ids)]; \
  print('componentes', sorted(d.name for d in c.iterdir() if d.is_dir()) if c.exists() else [], 'mal', mal); sys.exit(1 if mal else 0)"
grep -q 'CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y' sdkconfig.defaults
! grep -q '^CONFIG_NODO_UDP_LOG=y' sdkconfig.defaults
for w in "Build Firmware" "host tests + secret scan" "devcontainer image builds"; do
  echo "$w: $(gh run list -R rafaelrodWebpos/villa-nodo-clima-piloto -w "$w" -b main --status success -L 1 --json headSha --jq '.[0].headSha // "NINGUNO"')"
done   # cada workflow debe tener al menos un run verde en main (ninguno en NINGUNO)
```

## Comprobación de comportamiento (la que decide)

Abre una sesión `/build` con solo el repositorio. ¿Puede decir, sin preguntar
nada, la posición derivada del estado y el siguiente acto con cómo hacerlo?
La posición es 2 · Commissioning mientras la agenda tenga abierta alguna fila
que exige DUT ready o la puerta 03 no conste `OPEN`; si no, 3 · Build con su
ola y lo que espera su puerta. Si tiene que preguntar algo, la información que
le falta es el hallazgo.

## Trampas de este proyecto

- Capacidades del banco en `yes` copiadas de la documentación del testbench, sin un endpoint del banco que las reporte. Ejemplos: salida a Internet, bloqueo de SNTP, DNS propio, corte de alimentación, autenticación del broker.
- La dirección IP del banco escrita en un fichero versionado. Solo puede estar en `.env`.
- Evidencia del tipo `observed:` que solo podría venir de la placa, sin commit o antes de que la puerta 03 conste `OPEN`: la Fase 1 no toca el DUT; el commissioning sí, y deja su commit.
- El log UDP activado en la configuración de producción (choca con C-LOG-01).
- El patrón `build/` del `.gitignore` excluyendo `.claude/skills/build/` (ya pasó).
- El job verify con un trigger de pull request (repositorio público + runner self-hosted).

## Veredicto
`OPEN` · `SHUT` + hallazgos.
