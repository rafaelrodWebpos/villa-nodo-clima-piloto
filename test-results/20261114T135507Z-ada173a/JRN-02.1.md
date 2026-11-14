# JRN-02.1 — OTA a B1 y a B2

- imagen: `0.0.0-ada173a-bench` (variante bench, run CI None)
- broker del banco (abierto); tópicos bajo `sitio1/zona1/clima-f3c6d4/` y `homeassistant/sensor/clima-f3c6d4/`

- Precondiciones: grabar la imagen de la CI en SLOT1
- Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL
- El banco se une al AP abierto clima-f3c6d4 (intento 1)
- sta_join intento 1: ip del banco `192.168.4.2` (13:55:47.016 → 13:55:58.825 UTC)
- Precondiciones: POST / con los datos de un AP desechable nuevo
- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado

- Resetear el DUT y levantar el AP desechable (canal 1, con salida a Internet); esperar T11
- OTA A → B1, y 310 s de vigilancia (FR-OTA-06)
- 0.0.1-ota-test.2.1: en_curso a 0.29 s; ok; fw = 0.0.1-ota-test.2.1 a 4.2 s del ok (≤ 120 s); boot img=pendiente, E9; 310 s sin rollback
- B1 otra vez: rechazado:misma_version (FR-OTA-05)
- B1 sobre B1: rechazado:misma_version a 6.4 s
- OTA B1 → B2 (FR-OTA-02, segunda versión)
- 0.0.1-ota-test.2.2: en_curso a 0.26 s; ok; fw = 0.0.1-ota-test.2.2 a 4.1 s del ok (≤ 120 s); boot img=pendiente, E9
- log: `JRN-02.1-serie.log` (517 líneas)

**Resultado: PASS** — A → 0.0.1-ota-test.2.1 → misma_version → 0.0.1-ota-test.2.2; mismos tópicos, sin portal
