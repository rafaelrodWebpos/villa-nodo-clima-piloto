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

## Verificación independiente y ronda corta H-85 (2026-11-10)

Informe: `testing/verificacion-seguridad-fase-2.md` (S1 cerrable, sin puerta trasera, pendientes de
severidad baja). Cambio agrupado del FSD: 0.9.9 (`ddf8016`).

| Punto | Cambio | Commit | Comprobación | Regresión de banco |
|---|---|---|---|---|
| SEC-05, cliente lento | plazo total: corte a los 15 s, nunca más de 20 s con la última espera de 5 s (D25) | 038b813 | TC-POR-13 host con «1 byte por espera» y esperas alternas | 6 de 6 (`test-results/20261111T004519Z-038b813/`) |
| N-02 | el cierre de T24 corre en una tarea propia y apaga el AP antes de `httpd_stop` | 308d490 | revisión | 3 de 3 con TC-POR-12 (`test-results/20261111T005328Z-308d490/`) |
| N-01 | DNS con `SO_RCVTIMEO` de 1 s, `close()` y E14 «portal: dns detenido»; TC-POR-12 la exige a ≤ 5 s | fbb87c4 | E14 a 740 ms de T24 | 4 de 4 (`test-results/20261111T011057Z-fbb87c4/`) |
| SEC-04(a) | T26: con el cierre pendiente, un envío se responde «ocupado» sin probar la unión | 7a7402c | TC-CON-01 host | 6 de 6 (`test-results/20261111T012827Z-7a7402c/`) |
| SEC-06, host débil | DNS y HTTP solo para clientes de 192.168.4.0/24 dirigidos a 192.168.4.1; DNS ligado además a la interfaz del AP (`SO_BINDTODEVICE`) | 2450ac1 | TC-POR-14 host con (local, remota) | 11 de 11 (`test-results/20261111T013705Z-2450ac1/`) |
| N-03, N-04 | el DNS se liga en T02 y devuelve el resultado real; si falla, E14 «portal: dns no disponible» sin abortar; comentarios recolocados | fc5103a | TC-POR-12 comprueba que no aparezca | 9 de 9 (`test-results/20261111T020527Z-fc5103a/`) |

**Lo que el auditor dejó por verificar:**

- **lwIP de ESP-IDF 6.0.2 (fuentes del contenedor `espressif/idf:v6.0.2`).**
  - Es de host débil: si un paquete no es para la interfaz por la que entra, `ip4_input` recorre las demás (`ip4.c:612-633`). El desvío de SEC-06 era real.
  - `shutdown()` sobre UDP devuelve `EOPNOTSUPP` (`sockets.c:2751`). N-01 era real.
  - `SO_BINDTODEVICE` lo aplica `udp_input` (`udp.c:139`) y también lo admite la escucha TCP (`tcp_in.c:331`). Pero `esp_http_server` no da acceso a su socket de escucha, así que en el HTTP el filtro es por IP local y remota. Un origen falsificado de 192.168.4.0/24 no completa la conexión TCP, porque el SYN-ACK sale por el AP.
- **Acciones y digest.** Cada SHA es el commit del tag de su comentario (checkout v4.4.0, upload-artifact v4.6.2, download-artifact v4.3.0, comprobado con la API de GitHub). El digest `sha256:0d8c9773…cb67` es el de `espressif/idf:v6.0.2` en el registro y en Docker Hub.

**Observación del banco:** en la regresión de 2450ac1, 4 de unas 13 uniones del banco al AP del DUT
no recibieron IP del DHCP a tiempo. El banco se quedó con una dirección de enlace local
(169.254.x, en la evidencia) y la recibió al segundo intento. No se repitió en la regresión siguiente
(fc5103a, con el mismo cambio): 7 de 7 al primer intento. Esa dirección es del propio banco; no es
un dato de la red de la casa.
