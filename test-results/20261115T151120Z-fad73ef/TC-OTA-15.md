# TC-OTA-15 — Corte de alimentación durante la descarga OTA

- imagen: `0.0.0-fad73ef-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (15:32:54.912 → 15:33:06.418 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Aviso previo: el operador se pone junto a la placa
- Corte 1/1: aviso «desenchufa el USB-C de la placa»
- Corte 1/1: aviso «vuelve a enchufar el USB-C en la placa»
- Corte 1/1: AP del banco apagado ~20 s y escaneo Wi-Fi (no debe verse ningún clima-*)
- Corte 1/1: AP del banco encendido; esperar a que el nodo vuelva a publicar
- Vigilar 330 s (T23 vence a los 300 s) que no haya rollback ni reinicio
- log: `TC-OTA-15-serie-antes-del-corte.log` (4 líneas)
- corte 1: ausente 0.5 s tras la última muestra presente; Last Will 85.4 s (retenido: sí); reenchufe a 104 s; primer status `sitio1/zona1/clima-f3c6d4/status` reset=poweron uptime_s=1 a 0.6 s del reenchufe; primera medida a 3.0 s del encendido estimado; clima-* en el escaneo: ninguno; vuelta a publicar 3.8 s tras encender el AP; avisos: [True, True]
- último «ota: n %» antes del corte: — %
- primer status tras el reenchufe: fw=0.0.0-fad73ef-bench reset=poweron ota=ninguno
- 330 s después: 7 status, fw ['0.0.0-fad73ef-bench'], uptime_s monótono: True

**Resultado: FAIL** — IndexError: list index out of range
