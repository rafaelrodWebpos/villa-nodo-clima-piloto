# TC-MQTT-03 — Orden de conexión y retenidos

- imagen: `0.0.0-9ddfcb4-bench` (variante bench, run CI 42368845448)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (11:39:12.548 → 11:39:23.853 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Arrancar el broker, borrar los retenidos del nodo y suscribirse
- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Esperar un ciclo de medición en vivo (70 s)
- Suscriptor nuevo: configuraciones y medidas retenidas
- log: `TC-MQTT-03-serie.log` (59 líneas)
- log: `TC-MQTT-03-mqtt.log` (12 líneas)

## Resultado

- secuencia en vivo: ['<base>/status', '<base>/temperatura', '<base>/humedad', '<base>/punto_rocio', '<base>/temperatura', '<base>/humedad', '<base>/punto_rocio', '<base>/status']

**Resultado: FAIL** — AssertionError: solo 0 configuraciones de Discovery (FR-HA-01)
assert 0 >= 3
 +  where 0 = len([])
