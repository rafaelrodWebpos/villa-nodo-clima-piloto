# TC-WDT-01 — Estabilidad (corrida de humo, 15 min)

- imagen: `0.0.0-47a52ea-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (12:51:53.610 → 12:52:03.776 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- **corrida de humo** (NODO_WDT_HUMO=1): no cuenta como resultado de TC-WDT-01

- ventana: 900 s; cortes de 300 s: broker a t=300 s

- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Ventana de 0 h 15 min con 1 cortes
- Corte de broker 5 min (t=300 s)
- log: `TC-WDT-01-serie.log` (399 líneas)
- log: `TC-WDT-01-mqtt.log` (59 líneas)

## Resultado

- status en vivo: 13 (13 en la ventana); primero: uptime_s=4, lecturas=1, err_sensor=0, reset=usb; último: uptime_s=960, lecturas=17, err_sensor=0, reset=usb
- entre el primer y el último status: 955 s = 16 ciclos; Δlecturas = 16 (esperado 16 ± 2); Δerr_sensor = 0
- ciclos en OPERATIVO (status en vivo): 12; sin OPERATIVO: 4; publicaciones por medida: {'temperatura': 12, 'humedad': 12, 'punto_rocio': 12}
- corte de broker a t=300 s: primer status en vivo a 3.6 s de devolverlo
- uptime_s no creciente: ninguno; valores de reset: ['usb']
- líneas boot:/rst: en la ventana: 0; líneas con task_wdt: 0
- control de la consola: 15 líneas med: en la ventana; tramos de 10 min con < 5: ninguno

**Resultado: PASS** — 0.27 h, 1 cortes: 0 reinicios, uptime_s monótono, reset=usb, Δlecturas=16 (16 ± 2), publicaciones {'temperatura': 12, 'humedad': 12, 'punto_rocio': 12} con 12 ciclos en OPERATIVO
