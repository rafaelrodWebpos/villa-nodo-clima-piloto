# TC-CFG-02 — Cinco cortes de alimentación

- imagen: `0.0.0-9bcc519-bench` (variante bench, run CI 42153600255)

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2`
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Corte 1/5: aviso al operador

**Resultado: SKIP** — not done: la consola no capturó el arranque tras el corte 1 (instrumento, no el DUT)
