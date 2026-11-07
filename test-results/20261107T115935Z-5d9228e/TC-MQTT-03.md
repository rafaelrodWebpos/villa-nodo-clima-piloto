# TC-MQTT-03 — Orden de conexión y retenidos

- imagen: `0.0.0-5d9228e-bench` (variante bench, run CI 42370306092)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (12:05:43.570 → 12:05:55.332 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Arrancar el broker, borrar los retenidos del nodo y suscribirse
- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Esperar un ciclo de medición en vivo (70 s)
- Suscriptor nuevo: configuraciones y medidas retenidas
- log: `TC-MQTT-03-serie.log` (59 líneas)
- log: `TC-MQTT-03-mqtt.log` (18 líneas)

## Resultado

- secuencia en vivo: ['<base>/status', '<ha>/temperatura/config', '<ha>/humedad/config', '<ha>/punto_rocio/config', '<base>/temperatura', '<base>/humedad', '<base>/punto_rocio', '<base>/temperatura', '<base>/humedad', '<base>/punto_rocio']

**Resultado: PASS** — status → 3 configuraciones (§10.2, QoS 1) → medidas (QoS 0); configuraciones y último valor retenidos
