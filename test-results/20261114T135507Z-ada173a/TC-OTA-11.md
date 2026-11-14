# TC-OTA-11 — Wi-Fi perdido durante la descarga

- imagen: `0.0.0-ada173a-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (14:05:23.545 → 14:05:34.248 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Apagar el AP 30 s a mitad de descarga (: 30 %)
- Reset por la línea del banco: debe arrancar A en su partición
- log: `TC-OTA-11-serie.log` (173 líneas)
- primer status tras volver el AP: ota=error:red fw=0.0.0-ada173a-bench
- tras el reset: nodo: boot: clima-f3c6d4 fw=0.0.0-ada173a-bench reset=usb part=ota_0 img=valida (A en ota_0)

**Resultado: PASS** — T22, error:red en el primer status, A sigue y arranca en su partición
