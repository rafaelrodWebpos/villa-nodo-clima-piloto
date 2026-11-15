# JRN-01.7 — Corte de alimentación visto por MQTT

- imagen: `0.0.0-cfb249a` (variante production, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (17:20:26.870 → 17:20:39.100 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Arrancar el broker y suscribirse antes del corte (cualquier sitio/zona del nodo)
- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Corte 1/1: aviso «desenchufa el USB-C de la placa»

**Resultado: SKIP** — not done: el slot no quedó ausente en 600 s (corte 1 sin hacer)
