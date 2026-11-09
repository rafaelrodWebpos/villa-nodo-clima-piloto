# TC-WDT-01 — Estabilidad 24 h

- imagen: `0.0.0-17dc543-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (19:57:01.636 → 19:57:12.624 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- ventana: 86400 s; cortes de 300 s: broker a t=7200 s, wifi a t=21600 s, broker a t=36000 s, wifi a t=50400 s, broker a t=64800 s

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Ventana de 24 h 0 min con 5 cortes
- Corte de broker 5 min (t=7203 s)
- Corte de wifi 5 min (t=21612 s)
- Corte de broker 5 min (t=36022 s)
- Corte de wifi 5 min (t=50429 s)
- Corte de broker 5 min (t=64808 s)
- log: `TC-WDT-01-serie.log` (13406 líneas)
- log: `TC-WDT-01-mqtt.log` (5711 líneas)

## Resultado

- status en vivo: 1422 (1422 en la ventana); primero: uptime_s=4, lecturas=1, err_sensor=0, reset=usb; último: uptime_s=86460, lecturas=1442, err_sensor=0, reset=usb
- entre el primer y el último status: 86456 s = 1441 ciclos; Δlecturas = 1441 (esperado 1441 ± 2); Δerr_sensor = 0
- ciclos en OPERATIVO (status en vivo): 1421; sin OPERATIVO: 20; publicaciones por medida: {'temperatura': 1421, 'humedad': 1421, 'punto_rocio': 1421}
- corte de broker a t=7203 s: primer status en vivo a 3.4 s de devolverlo
- corte de wifi a t=21612 s: primer status en vivo a 26.1 s de devolverlo
- corte de broker a t=36022 s: primer status en vivo a 3.5 s de devolverlo
- corte de wifi a t=50429 s: primer status en vivo a 26.0 s de devolverlo
- corte de broker a t=64808 s: primer status en vivo a 3.3 s de devolverlo
- uptime_s no creciente: ninguno; valores de reset: ['usb']
- líneas boot:/rst: en la ventana: 3; líneas con task_wdt: 0
- control de la consola: 1440 líneas med: en la ventana; tramos de 10 min con < 5: ninguno

**Resultado: FAIL** — AssertionError: reinicio en la ventana: ['I (368) boot: Loaded app from partition at offset 0x20000', 'I (369) boot: Disabling RNG early entropy source...', 'I (485) nodo: boot: clima-f3c6d4 fw=0.0.0-17dc543-bench reset=usb part=ota_0 img=valida']
assert not ['I (368) boot: Loaded app from partition at offset 0x20000', 'I (369) boot: Disabling RNG early entropy source...', 'I (485) nodo: boot: clima-f3c6d4 fw=0.0.0-17dc543-bench reset=usb part=ota_0 img=valida']
