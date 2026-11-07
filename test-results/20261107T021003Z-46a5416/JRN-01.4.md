# JRN-01.4 — Conectar al broker y publicar status

- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/`

- Precondiciones: AP y broker del banco apagados
- Arrancar el broker, borrar los retenidos del nodo y suscribirse a sitio1/zona1/#
- Levantar el AP desechable (canal 1) y resetear el DUT
- Suscriptor nuevo: el status debe estar retenido
- log: `JRN-01.4-serie.log` (187 líneas)
- log: `JRN-01.4-mqtt.log` (15 líneas)

## Resultado

- primer mensaje: `sitio1/zona1/clima-f3c6d4/status` qos=1
- payload: `{"estado":"online","fw":"0.0.0-46a5416-bench","rssi":-38,"reset":"usb","uptime_s":193,"lecturas":4,"err_sensor":0,"ota":"ninguno","hora_valida":false}`
- mensajes del nodo en la ventana: 14

**Resultado: PASS** — T11, primer mensaje status online con los 9 campos (fw=0.0.0-46a5416-bench, reset=usb), retenido
