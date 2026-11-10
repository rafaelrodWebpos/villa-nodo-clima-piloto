# TC-POR-11 — Sin portal fuera de PORTAL y VALIDANDO

- imagen: `0.0.0-758ccbc-bench` (variante bench, run CI None)

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (23:28:56.044 → 23:29:07.046 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Reset con el AP apagado (CONECTANDO_WIFI) y escaneo
- El banco levanta el AP desechable; tras T08, GET http://<ip-dut>/ por el relé
- log: `TC-POR-11-serie.log` (194 líneas)

## Resultado

- escaneo en CONECTANDO_WIFI: 8 redes, clima-*: ninguna
- IP del DUT tras T08: `192.168.4.11`
- control positivo del relé (GET al banco por la red del AP): 200
- GET http://<ip-dut>/: ('sin respuesta', 'http: HTTP request failed: [Errno 111] Connection refused')

**Resultado: PASS** — sin clima-* en el escaneo y GET a 192.168.4.11 sin respuesta HTTP
