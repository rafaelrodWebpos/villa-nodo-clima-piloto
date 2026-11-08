# Regresión del banco con el fork propio — villa-1 (2026-11-08)

Fork `rafaelrodWebpos/Embedded-AI-Harness`, tag `villa-1` (`8966260`), sobre `db6a093` del
original (H-72 diseño, H-73 implementación, H-74 regresión). Añade `bench-ap-internet` y
`bench-sntp-block`; no cambia nada más. Diseño, seguridad y vuelta atrás: `docs/fork-villa.md`
en el fork.

## Instalación

| Paso | Resultado |
|---|---|
| Bloque A (instantánea, por el propietario) | `archivos-antes.tgz` 124235 bytes; `iptables-antes.rules` e `ip6tables-antes.rules` vacíos (ninguna tabla cargada); `ip_forward` = 0; ninguna regla MASQUERADE ni FORWARD antigua; los 8 módulos principales iguales a `db6a093` |
| Bloque B (instalación, por el propietario) | `install.sh --update` completo; por HTTP: `build` 8966260, `capabilities` con las dos, `internet: false`, `rules_ok: true`, cadena = un DROP; resto del banco 200 |

## Pruebas

| Punto | Resultado | Evidencia |
|---|---|---|
| FORK-01 valores por defecto | verde: apagado por defecto y tras `ap_stop`; 9 rangos privados cortados antes del ACCEPT; SNTP antes de cualquier ACCEPT; cuerpos no booleanos → 400; `rules_ok` en 12 pasos | `test-results/20261108T141629Z-660f6f5/FORK-01.md` |
| FORK-02 salida real y bloqueo de SNTP | verde: sincroniza a 13,4 s; `hora_valida` true y `ts` real (−0,4 s); bloqueado: 0 sincronizaciones en 75 s, 2 fallos, `hora_valida` false; desbloqueado: sincroniza a 5,0 s | `test-results/20261108T141629Z-660f6f5/FORK-02*` |
| FORK-03 LAN cerrada | verde: con la salida encendida el DUT no llega en 180 s al broker de prueba de la laptop en la LAN y sí sincroniza SNTP; control positivo: la Pi alcanza ese broker (log del broker, IP sustituidas por su papel). Regla temporal de Hyper-V puesta y quitada por el propietario | `test-results/20261108T151202Z-3b37ba6/` |
| JRN-01.0 … JRN-01.5 sobre el fork | verde los 6 (Home Assistant de prueba levantado y borrado) | `test-results/20261108T142118Z-660f6f5/` |
| TC-CON-08 sobre el fork | verde | `test-results/20261108T142118Z-660f6f5/TC-CON-08*` |
| Vuelta atrás (`sudo harness-volver-original`, por el propietario) | el script terminó con «Banco original restaurado» (solo lo imprime con 0 reglas HARNESS y sin capacidades en `/api/info`); por HTTP: `/api/info` en su forma original, `GET /api/wifi/internet` → 404, `ap_status` sin los campos del fork, resto 200 | — |
| Reinstalación (`install.sh --update`, por el propietario) | por HTTP: `build` 8966260, las dos capacidades, `internet: false`, `rules_ok: true`, resto 200 | — |

Imagen del DUT en las pruebas: `0.0.0-47a52ea-bench` (mismo firmware que main), grabada con
`--firmware-dir`.

## Notas

- El primer control positivo de FORK-03 (10:16) se diagnosticó como bloqueo del firewall de
  Hyper-V; el log del broker sugiere después que aquel intento sí llegó y que el «timed out»
  era la lectura HTTP. Con la regla temporal, el control quedó demostrado sin duda.
- Con el fork instalado, `bench-ap-internet` y `bench-sntp-block` pasan a `yes` en el plan. Si
  el banco vuelve al original, vuelven a `no`.
