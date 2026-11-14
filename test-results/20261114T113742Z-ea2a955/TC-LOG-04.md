# TC-LOG-04 — Sin log UDP en producción

- imagen: `0.0.0-ea2a955` (variante production, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (11:38:21.620 → 11:38:32.069 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Captura del tráfico del DUT durante el arranque y 3 ciclos (imagen de producción)

## Flujos del DUT (captura de cabeceras)

- UDP → 192.168.4.1:53 (unicast): 22
- TCP → 192.168.4.1:1883 (unicast): 56
- UDP → 255.255.255.255:67 (broadcast): 6

**Resultado: PASS** — por UDP solo 53, 67; ningún datagrama al 5555
