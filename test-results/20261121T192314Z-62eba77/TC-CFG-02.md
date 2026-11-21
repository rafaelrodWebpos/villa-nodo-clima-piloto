# TC-CFG-02 — Cinco cortes de alimentación

- imagen: `0.0.0-9e80669-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (19:28:03.597 → 19:28:15.324 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Arrancar el broker y suscribirse antes del primer corte (cualquier sitio/zona del nodo)
- Resetear el DUT y levantar el AP desechable (canal 1); esperar T11
- Corte 1/5: aviso «desenchufa el USB-C de la placa»
- Corte 1/5: aviso «vuelve a enchufar el USB-C en la placa»
- Corte 1/5: AP del banco apagado ~20 s y escaneo Wi-Fi (no debe verse ningún clima-*)
- Corte 1/5: AP del banco encendido; esperar a que el nodo vuelva a publicar
- Corte 2/5: aviso «desenchufa el USB-C de la placa»
- Corte 2/5: aviso «vuelve a enchufar el USB-C en la placa»
- Corte 2/5: AP del banco apagado ~20 s y escaneo Wi-Fi (no debe verse ningún clima-*)
- Corte 2/5: AP del banco encendido; esperar a que el nodo vuelva a publicar
- Corte 3/5: aviso «desenchufa el USB-C de la placa»
- Corte 3/5: aviso «vuelve a enchufar el USB-C en la placa»
- Corte 3/5: AP del banco apagado ~20 s y escaneo Wi-Fi (no debe verse ningún clima-*)
- Corte 3/5: AP del banco encendido; esperar a que el nodo vuelva a publicar
- Corte 4/5: aviso «desenchufa el USB-C de la placa»
- Corte 4/5: aviso «vuelve a enchufar el USB-C en la placa»
- Corte 4/5: AP del banco apagado ~20 s y escaneo Wi-Fi (no debe verse ningún clima-*)
- Corte 4/5: AP del banco encendido; esperar a que el nodo vuelva a publicar
- Corte 5/5: aviso «desenchufa el USB-C de la placa»
- Corte 5/5: aviso «vuelve a enchufar el USB-C en la placa»
- Corte 5/5: AP del banco apagado ~20 s y escaneo Wi-Fi (no debe verse ningún clima-*)
- Corte 5/5: AP del banco encendido; esperar a que el nodo vuelva a publicar
- log: `TC-CFG-02-mqtt.log` (97 líneas)
- log: `TC-CFG-02-serie.log` (335 líneas)

## Resultado

- corte 1: ausente 0.5 s tras la última muestra presente; Last Will 69.1 s (retenido: sí); reenchufe a 86 s; primer status `sitio1/zona1/clima-f3c6d4/status` reset=poweron uptime_s=1 a 0.5 s del reenchufe; primera medida a 3.0 s del encendido estimado; clima-* en el escaneo: ninguno; segundo arranque tras el enchufe (#86): ninguno; vuelta a publicar 5.0 s tras encender el AP; avisos: [True, True]
- corte 2: ausente 0.5 s tras la última muestra presente; Last Will 87.1 s (retenido: sí); reenchufe a 104 s; primer status `sitio1/zona1/clima-f3c6d4/status` reset=poweron uptime_s=1 a 0.4 s del reenchufe; primera medida a 3.0 s del encendido estimado; clima-* en el escaneo: ninguno; segundo arranque tras el enchufe (#86): ninguno; vuelta a publicar 5.0 s tras encender el AP; avisos: [True, True]
- corte 3: ausente 0.5 s tras la última muestra presente; Last Will 84.6 s (retenido: sí); reenchufe a 106 s; primer status `sitio1/zona1/clima-f3c6d4/status` reset=poweron uptime_s=1 a 0.3 s del reenchufe; primera medida a 3.0 s del encendido estimado; clima-* en el escaneo: ninguno; segundo arranque tras el enchufe (#86): ninguno; vuelta a publicar 4.8 s tras encender el AP; avisos: [True, True]
- corte 4: ausente 0.5 s tras la última muestra presente; Last Will 90.8 s (retenido: sí); reenchufe a 115 s; primer status `sitio1/zona1/clima-f3c6d4/status` reset=poweron uptime_s=60 a -114.5 s del reenchufe; primera medida a 177.0 s del encendido estimado; clima-* en el escaneo: ninguno; segundo arranque tras el enchufe (#86): {'t_desde_enchufe': 0.4, 'uptime_s': 1}; vuelta a publicar 4.8 s tras encender el AP; avisos: [True, True]
- corte 5: ausente 0.5 s tras la última muestra presente; Last Will 77.8 s (retenido: sí); reenchufe a 94 s; primer status `sitio1/zona1/clima-f3c6d4/status` reset=poweron uptime_s=1 a 0.4 s del reenchufe; primera medida a 3.0 s del encendido estimado; clima-* en el escaneo: ninguno; segundo arranque tras el enchufe (#86): ninguno; vuelta a publicar 5.0 s tras encender el AP; avisos: [True, True]

**Resultado: PASS** — 5 encendidos con status reset=poweron bajo sitio1/zona1/clima-f3c6d4/status; ningún portal
