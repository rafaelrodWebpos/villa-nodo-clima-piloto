# TC-OTA-15 — Corte de alimentación durante la descarga OTA

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (19:12:04.953 → 19:12:16.501 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Aviso previo: el operador se pone junto a la placa
- Corte 1/1: aviso «desenchufa el USB-C de la placa»

**Resultado: SKIP** — not done: el slot no quedó ausente en 600 s (corte 1 sin hacer)
