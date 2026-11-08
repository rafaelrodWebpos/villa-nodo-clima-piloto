# TC-MED-06 — Al reconectar, solo la lectura más reciente

- imagen: `0.0.0-17dc543-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (15:45:51.745 → 15:46:03.006 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- reloj del suscriptor (laptop) frente a pool.ntp.org: -0.84 s

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Esperar hora válida (status con hora_valida = true)
- Parar el broker 5 min
- Arrancar el broker; esperar el status online de la reconexión y 10 s más
- log: `TC-MED-06-serie.log` (199 líneas)
- log: `TC-MED-06-mqtt.log` (19 líneas)

## Resultado

- broker parado 300 s; suscriptor reconectado 1.4 s antes del status
- status de la reconexión a +3.5 s de arrancar el broker: `{"estado":"online","fw":"0.0.0-17dc543-bench","rssi":-45,"reset":"usb","uptime_s":367,"lecturas":7,"err_sensor":0,"ota":"ninguno","hora_valida":true}`
- mensajes por medida en [status, +5 s]: {'temperatura': 1, 'humedad': 1, 'punto_rocio': 1}
- edad (llegada − ts) de esos mensajes: {'temperatura': 7.1, 'humedad': 7.1, 'punto_rocio': 7.1} s
- mensajes tras la reconexión con ts de la ventana sin conexión: ninguno

**Resultado: PASS** — 1 mensaje por medida en la ventana; edades {'temperatura': 7.1, 'humedad': 7.1, 'punto_rocio': 7.1} s; ninguna lectura del corte publicada
