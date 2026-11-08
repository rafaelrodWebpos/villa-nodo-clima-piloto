# TC-TIME-03 — reevaluación de esta evidencia (H-76)

La ejecución de ab384dd salió en rojo en su primera aserción, `reset = poweron` en el primer
status tras el reenchufe, que no era del contrato. El propietario aprobó (H-76) sustituirla por
evidencia de corte real (slot ausente ≥ 5 s y uptime_s ≤ 5 en el primer status), cambiada en
el test en c32b832, y reevaluar esta misma evidencia sin repetir el corte.

Como la ejecución se paró en la primera aserción, las demás no llegaron a evaluarse en vivo;
se evalúan aquí con los valores que el propio test registró en `TC-TIME-03.md` y con
`TC-TIME-03-mqtt.log`:

| Aserción (test en c32b832) | Valor registrado | Resultado |
|---|---|---|
| slot ausente ≥ 5 s | 22 s | ✅ |
| uptime_s ≤ 5 en el primer status tras el reenchufe | 1 (reset = usb; el status sigue al Last Will de la sesión anterior, a +103,2 s) | ✅ |
| con SNTP bloqueado hay status y ninguno con hora_valida ≠ false | 5 status, 0 | ✅ |
| con SNTP bloqueado hay medidas y ninguna con ts no nulo | 15 medidas, 0 | ✅ |
| no falta ninguna publicación: temperaturas ≥ ⌊300/60⌋ − 1 | 5 ≥ 4 | ✅ |
| ninguna medida sin la clave ts | 0 | ✅ |
| primera medida con ts ≤ 90 s tras desbloquear | 62,5 s | ✅ |
| algún status con hora_valida = true tras desbloquear | a +62,6 s | ✅ |
| ningún ts con \|ts − llegada\| > 2 s (incluye 0 y 1970) | ninguno (la primera: +0,71 s) | ✅ |
| ningún ts null después del primero con ts | 0 | ✅ |

Además, en la consola: «sntp: fallo» cada 30 s con SNTP bloqueado y «sntp: sincronizado
ts=1794167087» a 303,8 s de uptime, unos 3,8 s después del desbloqueo.

**Resultado de la reevaluación: PASS.**

Observación del banco: tras reenchufar el USB-C a los 22 s, el primer status dijo
`reset = usb` y no `poweron` (en JRN-01.7, con 92 s sin alimentación, dijo `poweron`). Es
compatible con que el banco reabra el puerto USB del DUT tras la re-enumeración y lo resetee,
pariente de CR-TB-12.
