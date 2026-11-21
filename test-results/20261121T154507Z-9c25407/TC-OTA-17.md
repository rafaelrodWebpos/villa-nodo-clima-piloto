# TC-OTA-17 — Aborto de una OTA lenta y cmd_ota nuevo

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (16:36:36.936 → 16:36:49.231 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Cortar la salida a Internet: la descarga se queda esperando datos (≤ 30 s, FR-OTA-12)
- Broker apagado y encendido: T22 aborta con la tarea aún dentro de la lectura
- cmd_ota nuevo con la tarea vieja viva: error:red (A3-03)
- Devolver Internet; esperar a que la tarea vieja salga (≤ 30 s)
- Reset: la imagen abortada no es la de arranque (B-1)
- cmd_ota de B2 con la tarea vieja ya fuera: termina en fw = B2
- log: `TC-OTA-17-serie.log` (312 líneas)
- segundo cmd_ota con la tarea vieja viva: ota = en_curso
- tras el reset: I (433) nodo: boot: clima-f3c6d4 fw=0.0.0-9e80669-bench reset=usb part=ota_0 img=valida (A en ota_0)
- arranques vistos: [('0.0.0-9e80669-bench', 'ota_0'), ('0.0.1-ota-test.2.2', 'ota_1')]
- fw final: 0.0.1-ota-test.2.2

**Resultado: FAIL** — AssertionError: el cmd_ota con la tarea vieja viva no dio error:red: (1795279052.0103385, {'estado': 'online', 'fw': '0.0.0-9e80669-bench', 'rssi': -27, 'reset': 'usb', 'uptime_s': 30, 'lecturas': 1, 'err_sensor': 0, 'ota': 'en_curso', 'hora_valida': True})
assert ((1795279052.0103385, {'err_sensor': 0, 'estado': 'online', 'fw': '0.0.0-9e80669-bench', 'hora_valida': True, ...}) and 'en_curso' == 'error:red'
  
  - error:red
  + en_curso)
