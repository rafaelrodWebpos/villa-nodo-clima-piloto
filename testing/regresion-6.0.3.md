# Regresión completa con ESP-IDF 6.0.3: guion del sábado 21 y el domingo 22

Firmware: la imagen de banco y la de producción del commit vigente ese día, con ESP-IDF 6.0.3, A3-02, A3-03, B-1 y
el driver villa-2 `20b42df`. Banco: fork `6dffd70`, instalado el 2026-11-19. Solo el SLOT1; el SLOT2 no se toca.
Las pruebas se lanzan en contenedores desacoplados, una tanda tras otra.

## Sábado 21: pruebas automáticas, sin el propietario

| Tanda | Pruebas | Duración aprox. |
|---|---|---|
| A. Recorrido y portal | JRN-01.0 a 01.6, TC-POR-02, 05, 07, 09, 11, 12, TC-CON-07, TC-CON-11, TC-CON-14, TC-HW-02, TC-HW-03 | 1 h |
| B. Conectividad y MQTT | TC-CON-03, 06, 08, 09, 10, TC-MQTT-03, TC-MQTT-05, TC-MED-01, TC-MED-02, TC-MED-06, TC-LOG-03, TC-LOG-04, TC-LOG-08 | 1 h 30 min |
| C. Hora y watchdog | TC-TIME-03, 05, 06, 08, TC-WDT-02 | 40 min |
| D. OTA | JRN-02.1, JRN-02.2, TC-OTA-06 a 14, **TC-OTA-17 (nuevo)** | 2 h |
| E. Largas | TC-CON-12 (70 min), TC-TIME-04 (2 h o más) | 3 h 30 min |
| F. Ensayo de `verify` | journey `-m journey` y TC-OTA-14 con la imagen de producción | 30 min |

En total son unas 9 a 10 h. JRN-01.0 ahora exige el arranque a 80 MHz.

## Domingo 22: visita, con el propietario junto al banco

| # | Prueba | Qué hace el propietario | Duración |
|---|---|---|---|
| 1 | iPhone, FR-POR-02 (la evidencia H-83 venció por el cambio de lwIP) | los pasos de `visita-final-fase-3.md` | 10 min |
| 2 | JRN-01.7, que ahora también exige que no haya un segundo arranque tras enchufar (#86) | desenchufar y enchufar, 1 vez | 10 min |
| 3 | TC-CFG-02 y TC-MQTT-04, en la misma sesión que la 2 | 5 cortes | 30 min |
| 4 | TC-SEN-04, el SDA del SHT41 | soltar y poner el Dupont | 10 min |
| 5 | TC-OTA-15, corte durante la descarga | desenchufar con el segundo aviso | 15 min |

En total, 1 h 15 min. Antes de la visita yo dejo el SLOT1 en PORTAL para el iPhone.

## Lo que decide el propietario

- **TC-WDT-01, 24 h** (aceptación 22.1-2). Si se repite, ocupa el SLOT1 un día entero y no cabe junto con la
  visita del domingo. Opciones:
  - (a) arrancarla el sábado a las 6:00 y que termine el domingo a las 6:00; las tandas automáticas pasan a la
    noche del domingo, después de la visita;
  - (b) no repetirla y dejarla como salvedad, porque el watchdog y su código no cambiaron (solo ESP-IDF);
  - (c) hacerla otro día.
- **TC-SEN-03 y TC-SEN-05:** la prueba de la sal dura 30 min y exige preparar el sensor. Se repiten solo si usted lo pide,
  porque el código del sensor no cambió.
- **El tag v0.0.2:** lo crea usted cuando todo esté en verde, como con v0.0.1 (runner levantado durante la release).
