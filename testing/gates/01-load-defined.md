# Puerta: Load defined (cierra la Fase 0)

**Exclusión permanente:** solo artefactos commiteados. Nada de memoria, transcripciones ni relato del autor.

FSD: `docs/Functionality/FSD-nodo-clima.md`. IDs: `FR-<ÁREA>-nn`, `NFR-<ÁREA>-nn`, `C-<ÁREA>-nn`, `T-nn`.

## Requisitos

| # | Debe ser cierto | Dónde mirar | Evidencia |
|---|---|---|---|
| 1 | Todo Must/Should tiene contrato con columna o campo «No debe ocurrir» / `prohibited_outcomes` | FSD, capítulo de cada requisito | La fila de la tabla de contratos o un bloque `id:` YAML con su ID |
| 2 | Toda fila T01–T23 tiene estado, evento, siguiente, límite y «No debe ocurrir»; la matriz §6.4 no tiene celdas vacías | FSD §6.3, §6.4 | Tabla completa |
| 3 | No queda ningún `(propuesto` sin decidir ni ningún `(assumed)` | FSD | grep |
| 4 | No hay `{{parámetros}}` sin enlazar (salvo las plantillas `{{ value_json.* }}` de HA) | FSD | grep |
| 5 | Cada fase de §3 se puede empezar con lo que entregan las anteriores | FSD §3 frente a los contratos | Los criterios de salida citan solo IDs cuyos contratos no usan capacidades de fases posteriores |
| 6 | Existen los tres planos y `docs/00-Overview.md` | `docs/` | ficheros |
| 7 | El perfil de amenazas (§19.1) precede a los requisitos de seguridad | FSD §19 | orden |

## Comprobaciones mecánicas

```bash
F=docs/Functionality/FSD-nodo-clima.md
test -f docs/00-Overview.md && ls docs/Method/AI-Workflow.md docs/UserDocumentation/Manual-de-usuario.md
! grep -n '(propuesto\b' "$F" | grep -v 'propuesto, Dnn\|propuesto por el paquete'
! grep -n '(assumed)' "$F"
! grep -o '{{[^}]*}}' "$F" | grep -v 'value_json'
# Todo ID definido aparece en una fila de contrato o en un bloque id: YAML
python3 - "$F" <<'PY'
import re,sys
s=open(sys.argv[1],encoding='utf-8').read()
ids=re.findall(r'^- \*\*((?:FR|NFR|C)-[A-Z]+-\d+)\*\* \[',s,re.M)+re.findall(r'^\| (C-[A-Z]+-\d+) \[',s,re.M)
cov=set(re.findall(r'^id: (\S+)',s,re.M))
for row in re.findall(r'^\| ([A-Z]+-[A-Z]+-\d+(?:[/, ]+(?:[A-Z]+-[A-Z]+-)?\d+)*) \|',s,re.M):
    for x in re.split(r',\s*',row):
        if '/' in x: b,_,n=x.rpartition('-'); cov|={b+'-'+p for p in n.split('/')}
        else: cov.add(x)
miss=[i for i in ids if i not in cov]; print(len(ids),"IDs; sin contrato:",miss); sys.exit(1 if miss else 0)
PY
```

## Comprobaciones de juicio (cita lo que leíste)

- Elige 5 contratos al azar, incluidos uno de §6.6 y uno de §7.4. ¿Podría alguien competente montar un rig a partir de cada uno sin leer el código? Cita el estímulo y la observación.
- ¿Algún contrato de la Fase 1 depende de MQTT, de la OTA o de Home Assistant? Si es así, es un defecto de secuencia.
- ¿Hay palabras vagas (adecuado, robusto, razonable, suficiente, funcionamiento normal…) en las líneas de requisito?

## Trampas de este proyecto

- Contratos de la Fase 1 que observaban por MQTT (ya pasó una vez: FR-MED-01, FR-POR-06).
- Valores marcados como propuestos que no estaban en la tabla de decisiones (pasó con D21/D22).
- Un ejemplo con datos reales de la vivienda (SSID, IP, zona) en un repositorio público.

## Veredicto
`OPEN` · `SHUT` + hallazgos.
