# JRN-01.7 — Corte de alimentación visto por MQTT

- imagen: `0.0.0-3f2eac8-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (11:15:58.307 → 11:16:08.006 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Arrancar el broker y suscribirse antes del corte (cualquier sitio/zona del nodo)
- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Corte 1/1: aviso «desenchufa el USB-C de la placa»
- Corte 1/1: aviso «vuelve a enchufar el USB-C en la placa»
- Corte 1/1: AP del banco apagado ~20 s y escaneo Wi-Fi (no debe verse ningún clima-*)
- Corte 1/1: AP del banco encendido; esperar a que el nodo vuelva a publicar
- log: `JRN-01.7-mqtt.log` (23 líneas)
- log: `JRN-01.7-serie.log` (174 líneas)

## Resultado

- corte 1: ausente 0.5 s tras la última muestra presente; Last Will 78.3 s (retenido: sí); reenchufe a 92 s; primer status `sitio1/zona1/clima-f3c6d4/status` reset=poweron uptime_s=1 a 0.7 s del reenchufe; primera medida a 3.0 s del encendido estimado; clima-* en el escaneo: ninguno; vuelta a publicar 4.0 s tras encender el AP; avisos: [True, True]

**Resultado: PASS** — reset=poweron bajo sitio1/zona1/clima-f3c6d4/status, sin portal, primera medida a 3.0 s del encendido estimado
