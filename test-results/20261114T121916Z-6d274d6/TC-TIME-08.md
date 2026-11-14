# TC-TIME-08 — Reinicio sin SNTP: hora no válida

- imagen: `0.0.0-6d274d6-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (12:21:42.986 → 12:21:54.439 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Bloquear SNTP y enviar «reiniciar» por la consola
- log: `TC-TIME-08-serie.log` (147 líneas)
- boot tras «reiniciar»: reset=sw
- hora_valida en los status tras el reinicio: [False, False, False]
- «sntp: sincronizado» tras el reinicio: 1

**Resultado: FAIL** — AssertionError: se sincronizó con SNTP bloqueado
assert not True
 +  where True = any(<generator object test_tc_time_08_reboot_without_sntp.<locals>.<genexpr> at 0x766711435b10>)
