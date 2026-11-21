# TC-LOG-04 — Sin log UDP en producción

- imagen: `0.0.0-9e80669` (variante production, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (16:56:20.729 → 16:56:31.256 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Captura del tráfico del DUT durante el arranque y 3 ciclos (imagen de producción)

## Flujos del DUT (captura de cabeceras)

- UDP → 192.168.4.1:53 (unicast): 24
- TCP → 192.168.4.1:1883 (unicast): 46
- UDP → 255.255.255.255:67 (broadcast): 2

**Resultado: PASS** — por UDP solo 53, 67; ningún datagrama al 5555
