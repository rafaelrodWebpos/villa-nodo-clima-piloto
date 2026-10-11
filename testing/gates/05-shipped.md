# Puerta: Shipped (release)

**Exclusión permanente:** solo artefactos commiteados y respuestas en vivo de GitHub. Nada de memoria, transcripciones ni relato del autor.

## Requisitos

| # | Debe ser cierto | Dónde mirar | Evidencia |
|---|---|---|---|
| 1 | La release `vX.Y.Z` se construyó a partir del commit etiquetado, en `espressif/idf:v6.0.2` | run de `Build Firmware` del tag | El job build en verde con ese `GITHUB_SHA` |
| 2 | El job verify se ejecutó con los bytes de esa ejecución y el journey pasó | mismo run, job `verify` | `success`; nada de `skipped` |
| 3 | La release se publicó solo después de verify | job `release` | `needs: [build, verify]`, en verde |
| 4 | La imagen publicada es la de producción: sin `NODO-BENCH-IMAGE` (C-LOG-01) | asset `firmware_vX.Y.Z.bin` | `! grep -q NODO-BENCH-IMAGE` |
| 5 | La versión del binario coincide con el tag | asset | `strings` contiene `X.Y.Z` |

## Comprobaciones mecánicas

```bash
T=vX.Y.Z
gh run list -R rafaelrodWebpos/villa-nodo-clima-piloto -w "Build Firmware" --json headBranch,conclusion,databaseId --jq ".[]|select(.headBranch==\"$T\")"
gh release download "$T" -R rafaelrodWebpos/villa-nodo-clima-piloto -p 'firmware_v*.bin' -D /tmp/rel
! grep -q NODO-BENCH-IMAGE /tmp/rel/firmware_v*.bin && strings /tmp/rel/firmware_v*.bin | grep -q "${T#v}"
```

## Trampas de este proyecto

- Banco apagado durante verify: es `not done`, no un fallo. No se publica nada; relanza el job con el banco encendido.
- Publicar a mano una release sin verify.

## Veredicto
`OPEN` · `SHUT` + hallazgos.
