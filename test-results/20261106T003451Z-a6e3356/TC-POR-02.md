# TC-POR-02 — GET / sirve el formulario

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- Precondiciones: el DUT tiene configuración; P-NVS-ERASE y reset
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-a6e3356-bench`
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2`
- la API del banco sigue respondiendo tras sta_join (ruta de eth0 intacta)
- GET http://192.168.4.1/ por el relé HTTP del banco
- respuesta: HTTP 200, 3510 bytes, `TC-POR-02-get.html`
- campos (name): ['mqtt_host', 'mqtt_pass', 'mqtt_port', 'mqtt_user', 'sitio', 'wifi_pass', 'wifi_ssid', 'zona']

**Resultado: PASS** — GET / en clima-f3c6d4: los 8 campos de §17, secretos vacíos
