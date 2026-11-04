# TC-POR-02 — GET / sirve el formulario

- Precondiciones: reset; el DUT debe arrancar en PORTAL
- DUT en PORTAL: `clima-f3c6d4`, fw `0.0.0-bench`
- El banco se une al AP abierto clima-f3c6d4
- sta_join: ip del banco en la red del portal `192.168.4.3`
- la API del banco sigue respondiendo tras sta_join (ruta de eth0 intacta)
- GET http://192.168.4.1/ por el relé HTTP del banco

**Resultado: FAIL** — CommandError: http: HTTP request failed: [Errno 111] Connection refused
