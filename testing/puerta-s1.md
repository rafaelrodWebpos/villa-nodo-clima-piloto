# Puerta de seguridad S1 — registro

- **Origen:** `testing/auditoria-seguridad-fase-2.md` (auditoría independiente sobre `d4236cc`);
  decisiones del propietario H-81 a H-84; FSD 0.9.8 (§3.5, §19.3).
- **Estado:** todos los criterios de §3.5 en verde (2026-11-10). La Fase 3 no se ha empezado.

## Hallazgos con cambio

| Hallazgo | Requisito | Commit | Tests | Resultado |
|---|---|---|---|---|
| SEC-04 — portal abierto sin límite | FR-POR-08, T24, T25 | 758ccbc | TC-CON-01 (host), TC-POR-12 (banco) | PASS: T24 a 600 000 ms de T02, AP fuera, medición sigue, sin NVS ni reinicio, reabierto tras un reset |
| SEC-05 — POST que retiene el servidor | FR-POR-09 | e83d355 | TC-POR-13 (host) | PASS |
| SEC-06 — DNS y HTTP alcanzables por el STA | FR-POR-10 | d64e5a3 | TC-POR-14 (host) + revisión | PASS |
| SEC-07 — STA sin umbral de autenticación | FR-CON-07 | 02de0f8 | TC-CON-13 (host), TC-CON-14 (banco, AP gemelo con el SSID de prueba, H-83) | PASS |
| SEC-08 — acciones por etiqueta, imagen sin digest, pip sin hash, release con acción de terceros | — (CI) | c1914db | las tres CI en verde, incluida la construcción del devcontainer | PASS |
| SEC-09 — inputs interpolados en el script | — (CI) | 8512553 | control: el workflow con `0.1.0"; echo INYECTADO; "` se rechazó (run 42915750487) | PASS |
| SEC-10, SEC-11 — rollback y política OTA | C-BLD-04, FR-OTA-03, -05, -13, -14 | 316a70b (FSD) | Fase 3 | sin implementar (Fase 3) |

## Regresión de banco

| Tras | Imagen | Tests | Resultado | Evidencia |
|---|---|---|---|---|
| SEC-07 | 0.0.0-02de0f8-bench | JRN-01.0 a 01.4, TC-CON-14 | 6 de 6 | `test-results/20261110T230652Z-02de0f8/` |
| SEC-04 | 0.0.0-758ccbc-bench | JRN-01.0 a 01.2, TC-POR-02, 05, 07, 09, 11, TC-CON-07, TC-POR-12 | 10 de 10 | `test-results/20261110T232408Z-758ccbc/` |
| SEC-05 | 0.0.0-e83d355-bench | JRN-01.0 a 01.2, TC-POR-05, 09, TC-CON-07 | 6 de 6 | `test-results/20261110T234713Z-e83d355/` |
| SEC-06 | 0.0.0-d64e5a3-bench | JRN-01.0 a 01.3, TC-POR-02, 05, 07, 09, 11, TC-CON-07, TC-POR-12 | 11 de 11 | `test-results/20261110T235539Z-d64e5a3/` |

Una ejecución de la regresión de SEC-07 se cortó al cerrarse la ventana antes de TC-CON-14;
se descartó entera (no cuenta) y se repitió.

## Hallazgos sin código

SEC-01, SEC-02, SEC-03 y SEC-12 a SEC-15: riesgos aceptados o revisión antes de cada release,
en FSD §19.3. SEC-01 se verificó el 2026-11-10: aprobación de workflows exigida a todos los
colaboradores externos y ningún runner registrado.

## Salvedades

- **FR-POR-02 con la evidencia caducada.** SEC-04, SEC-05 y SEC-06 cambian `components/portal`,
  y eso caduca la prueba del teléfono H-51 (TC-POR-08). Por H-83 se repite una sola vez al final
  de la Fase 3, con las demás pruebas físicas de esa fase.
- **SEC-07 no era explotable en ESP-IDF 6.0.2.** TC-CON-14 también pasó sobre la imagen anterior
  al arreglo (`test-results/20261110T224654Z-316a70b/`): el driver ya subía el umbral a WPA2
  cuando hay clave. El arreglo lo hace explícito.
- **SEC-05 y SEC-06 solo en host.** El relé HTTP del banco no puede mandar un cuerpo a medias, y
  con una sola radio el banco no habla con el DUT por la IP del STA. El DNS cautivo no tiene
  prueba de banco (`bench-portal-dns` en no); en la regresión no apareció ningún error al ligarlo
  a 192.168.4.1.
- **SEC-08, release.** `gh release create` solo corre con un tag `v*`: se comprobará en el primer
  tag (§19.3).
