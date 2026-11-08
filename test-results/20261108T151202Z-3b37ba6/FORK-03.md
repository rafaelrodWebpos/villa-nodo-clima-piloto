# FORK-03 — La LAN de la casa queda cerrada

- imagen: `0.0.0-47a52ea-bench` (variante bench, run CI None)
- broker de prueba en Docker en la laptop, en su IP de la LAN (<ip-laptop>), puerto 1883

- Precondiciones: grabar la imagen; aprovisionar el DUT con el broker de la laptop
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (15:12:33.298 → 15:12:44.552 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Control positivo: la Pi abre una conexión al broker de la laptop por la LAN (relé HTTP)
- Resetear el DUT, levantar el AP y encender la salida a Internet
- Observar 180 s
- log: `FORK-03-serie.log` (188 líneas)

## Resultado

- salida encendida durante la ventana: internet=True sntp_blocked=False lan_blocked=True rules_ok=True reglas=15; al final: internet=True sntp_blocked=False lan_blocked=True rules_ok=True reglas=15
- relé HTTP del banco hacia <ip-laptop>:1883 (control, ver log del broker): CommandError
- suscriptor del test conectado al broker de la laptop: 1 vez/veces
- SNTP del DUT en la misma sesión: `I (8275) nodo: sntp: sincronizado ts=1794150790`
- mensajes del DUT en el broker de la laptop: 0
- líneas de la consola sobre el broker (las 5 primeras): ['I (5225) nodo: con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)', 'I (5245) nodo: mqtt: intento 1', 'E (15265) mqtt_client: Error transport connect', 'I (15265) nodo: con: CONECTANDO_BROKER -> CONECTANDO_BROKER (mqtt_down)', 'I (16265) nodo: mqtt: intento 2']

**Resultado: PASS** — con la salida encendida el DUT sale a Internet (SNTP) y no llega al broker de la LAN en 180 s
