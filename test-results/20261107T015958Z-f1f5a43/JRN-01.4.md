# JRN-01.4 — Conectar al broker y publicar status

- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/`

- Precondiciones: AP y broker del banco apagados
- Arrancar el broker, borrar los retenidos del nodo y suscribirse a sitio1/zona1/#
- Levantar el AP desechable (canal 1) y resetear el DUT
- Suscriptor nuevo: el status debe estar retenido
- log: `JRN-01.4-serie.log` (174 líneas)
- log: `JRN-01.4-mqtt.log` (0 líneas)

**Resultado: FAIL** — AssertionError: sin con: CONECTANDO_BROKER -> OPERATIVO (mqtt_up) en 60 s (T11)
assert None
