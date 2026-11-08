# JRN-01.4 — Conectar al broker y publicar status

- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/`

- Precondiciones: AP y broker del banco apagados
- Arrancar el broker, borrar los retenidos del nodo y suscribirse a sitio1/zona1/#
- Resetear el DUT y levantar el AP desechable (canal 1)
- Suscriptor nuevo: el status debe estar retenido
- log: `JRN-01.4-serie.log` (150 líneas)
- log: `JRN-01.4-mqtt.log` (5 líneas)

## Resultado

- primer mensaje: `sitio1/zona1/clima-f3c6d4/status` qos=1 a +14.71 s del reset
- payload: `{"estado":"online","fw":"0.0.0-47a52ea-bench","rssi":-37,"reset":"usb","uptime_s":4,"lecturas":1,"err_sensor":0,"ota":"ninguno","hora_valida":false}`
- mensajes del nodo en la ventana: 4
- status online: 1; Last Will offline: 0 (informativo: un segundo arranque daría 2 y 1)

**Resultado: PASS** — T11, primer mensaje status online con los 9 campos (fw=0.0.0-47a52ea-bench, reset=usb), retenido
