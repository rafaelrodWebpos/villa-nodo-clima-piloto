# Puerta: Ready for shipment (cierra la Fase 3)

**Exclusión permanente:** solo artefactos commiteados y respuestas en vivo. Nada de memoria, transcripciones ni relato del autor.

## Requisitos

| # | Debe ser cierto | Dónde mirar | Evidencia |
|---|---|---|---|
| 1 | Todo requisito del FSD está cumplido: todos los tests que lo verifican están en `successful`, con «No debe ocurrir» comprobado | plan × FSD | `verifies` cubre todos los IDs del FSD; ningún test necesario en `failed` o `not done` |
| 2 | Toda fila T01–T23 tiene al menos un test de transición en `successful` | plan | `verifies` contiene cada `T-nn` |
| 3 | El journey JRN-01.* está en verde con el commit actual | plan | `status: successful`, `commit` = HEAD |
| 4 | Reconciliación vacía en ambos sentidos | plan `impl:` frente a `tests/` | Ningún `impl:` vacío; ningún ejecutable sin `impl:` que apunte a él |
| 5 | La OTA está probada en bench+ o en field (no queda sin probar) | plan, TC-OTA-* | `tier` y `status` |
| 6 | El manual describe el sistema construido; su línea de estado no dice «no hay nada desplegable» | `docs/UserDocumentation/Manual-de-usuario.md` | capítulos 3–6 escritos |
| 7 | Todos los tests del nivel host en verde en CI con HEAD | GitHub | run de `host tests + secret scan` |

## Comprobaciones mecánicas

```bash
python3 - <<'PY'
import yaml,re
p=yaml.safe_load(open('testing/test-plan.yaml')); s=open('docs/Functionality/FSD-nodo-clima.md').read()
ids=set(re.findall(r'\*\*((?:FR|NFR|C)-[A-Z]+-\d+)\*\* \[',s))|set(re.findall(r'^\| (C-[A-Z]+-\d+) \[',s,re.M))|set(re.findall(r'^\| (T\d\d) \|',s,re.M))
ver={v for t in p['tests'] for v in t.get('verifies',[])}
print('sin test:',sorted(ids-ver)); print('no successful:',[t['id'] for t in p['tests'] if t.get('status')!='successful'])
print('impl vacío:',[t['id'] for t in p['tests'] if not t.get('impl')])
PY
```

## Trampas de este proyecto

- Un test de recuperación que pasa porque el nodo se recuperó reiniciando (FR-CON-01 lo prohíbe).
- Que la «recuperación» sea un mensaje retained antiguo.
- Tests OTA en verde contra el servidor del banco en vez de contra GitHub real (FR-OTA-11).
- Waves: tests negative escritos con el journey todavía en rojo.

## Veredicto
`OPEN` · `SHUT` + hallazgos.
