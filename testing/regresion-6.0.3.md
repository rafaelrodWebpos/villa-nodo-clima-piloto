# Regresión completa con ESP-IDF 6.0.3: guion del sábado 21 y el domingo 22

Firmware: la imagen de banco y la de producción del commit vigente ese día, con ESP-IDF 6.0.3, A3-02, A3-03, B-1 y
el driver villa-2 `20b42df`. Banco: fork `6dffd70`, instalado el 2026-11-19. Solo el SLOT1; el SLOT2 no se toca.
Las pruebas se lanzan en contenedores desacoplados, una tanda tras otra.

## Orden acordado (propietario, 2026-11-19)

Todo corre en el SLOT1, en **una sola cadena desacoplada**: un contenedor lanzado una vez que corre las tandas una
tras otra, sin esperar a nadie. La laptop tiene que quedarse encendida todo el fin de semana. La cadena se lanza
solo después del aviso del propietario de que terminó la prueba de 24 h de AGUA.

| Tanda | Pruebas | Inicio y fin previstos |
|---|---|---|
| 0. Watchdog 24 h | TC-WDT-01 (aceptación 22.1-2) | viernes 20, ~18:15 → sábado 21, ~18:20 |
| A. Recorrido y portal | JRN-01.0 a 01.6, TC-POR-02, 05, 07, 09, 11, 12, TC-CON-07, TC-CON-14, TC-HW-02, TC-HW-03 | sábado ~18:20 → ~19:20 |
| B. Conectividad y MQTT | TC-CON-03, 06, 08, 09, 10, TC-MQTT-03, TC-MQTT-05, TC-MED-01, TC-MED-02, TC-MED-06, TC-LOG-03, TC-LOG-08 | ~19:20 → ~20:40 |
| C. Hora y watchdog | TC-TIME-05, 06, 08, TC-WDT-02 | ~20:40 → ~21:10 |
| D. OTA | JRN-02.1, JRN-02.2, TC-OTA-06 a 13, TC-OTA-17 (nuevo) | ~21:10 → ~23:10 |
| E. Largas | TC-CON-11 (AP apagado 60 min), TC-CON-12 (70 min), TC-TIME-04 (2 h o más) | ~23:10 → domingo 22, ~03:25 |
| F. Imagen de producción | ensayo de `verify` (`-m journey`), TC-LOG-04, TC-OTA-14 | domingo ~03:25 → ~04:05 |

La lanza `scripts/regresion/cadena.sh <run del build de banco> <run del build de producción> <sha7>`, en un solo
contenedor (`docker logs cadena`), con una salida por tanda en `test-results/cadena-<fecha>/`.

- **Las horas son aproximadas:** cada tanda empieza cuando termina la anterior.
- **Si una prueba falla, la cadena sigue** (sin `-x`), y el domingo por la mañana reviso los resultados antes de la visita.
- **TC-MQTT-04 va el domingo**, en la misma sesión que los cortes, porque usa sus Last Will.
- **JRN-01.0 ahora exige el arranque a 80 MHz.**

## Domingo 22: visita, con el propietario junto al banco

| # | Prueba | Qué hace el propietario | Duración |
|---|---|---|---|
| 1 | iPhone, FR-POR-02 (la evidencia H-83 venció por el cambio de lwIP) | los pasos de `visita-final-fase-3.md` | 10 min |
| 2 | JRN-01.7, que ahora también exige que no haya un segundo arranque tras enchufar (#86) | desenchufar y enchufar, 1 vez | 10 min |
| 3 | TC-CFG-02 y TC-MQTT-04, en la misma sesión que la 2 | 5 cortes | 30 min |
| 4 | TC-SEN-04, el SDA del SHT41 | soltar y poner el Dupont | 10 min |
| 5 | TC-OTA-15, corte durante la descarga | desenchufar con el segundo aviso | 15 min |
| 6 | TC-TIME-03, corte con SNTP bloqueado | desenchufar y enchufar con los avisos | 10 min |

En total, 1 h 25 min. Antes de la visita yo dejo el SLOT1 en PORTAL para el iPhone.

## Salvedades (propietario, 2026-11-19)

- **TC-SEN-03 y TC-SEN-05 no se repiten:** el código del sensor no cambió en este paquete (ESP-IDF 6.0.3, A3-02,
  A3-03, B-1, #52 y #86). Su último verde sigue valiendo, como salvedad.
- **TC-WDT-01 sí se repite** (tanda 0).
- **El tag v0.0.2** lo crea el propietario cuando todo esté en verde, como con v0.0.1 (runner levantado durante la release).
