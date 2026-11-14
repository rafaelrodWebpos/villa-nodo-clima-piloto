# JRN-02.2 — Rollback de una imagen que no llega a OPERATIVO

- imagen: `0.0.0-22fda6b-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (18:55:18.232 → 18:55:30.315 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- Esperar el rollback (T23, ≤ 300 s desde el boot de B)
- 15 min de vigilancia tras el primer status de A
- log: `JRN-02.2-serie.log` (312 líneas)
- boot de B (pendiente) → «ota: rollback»: 300.0 s (≤ 300 s)
- de vuelta: nodo: boot: clima-f3c6d4 fw=0.0.0-22fda6b-bench reset=sw part=ota_0 img=valida
- 15 min: 16 status, fw ['0.0.0-22fda6b-bench'], uptime_s monótono: True; boot: posteriores 0

**Resultado: PASS** — rollback a 300 s del boot de B; A estable 15 min
