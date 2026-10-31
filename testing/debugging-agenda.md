# Agenda de depuración — Nodo Clima Piloto

Piezas **del proyecto** que todavía no se han visto funcionar aquí. Mientras una
siga abierta, un test que falle puede estar midiendo el montaje y no el código.
La lista la dio el propietario en la pregunta 1 del harness (2026-10-31).
`/commission` la trabaja de arriba abajo y la vacía.

El testbench no aparece en esta lista. Sus capacidades se declaran tal como el
banco las reporta (`testing/test-plan.yaml` → `capabilities`) y este proyecto
no las prueba. La alimentación (USB del Pi) y la red (router de casa) ya
funcionan y tampoco aparecen.

Cada punto cierra una capacidad `unproven` del plan. Cuando se cierra, se anota
la fecha, el commit y la evidencia, y la capacidad pasa a `yes`.

| # | Pieza | Capacidad | Sin probar porque | Se prueba con | Estado |
|---|---|---|---|---|---|
| 1 | Waveshare ESP32-S3-DEV-KIT-N8R8 en SLOT1 | `dut-board` | El banco la lista presente e idle (USB-JTAG `303a:1001` y CH343 `1a86:55d3`), pero nadie ha leído el chip: no se sabe si es la unidad de C-HW-01 | Lectura del chip por el banco: ESP32-S3, flash de 8 MB (C-HW-02) y PSRAM de 8 MB; MAC anotada. Después, el camino de ida: imagen de banco del último run verde de la CI → flash por el banco → `NODO-BENCH-IMAGE` e `Init complete` en UART0 y en USB-Serial/JTAG (C-HW-08). Si no coincide, se para: placa equivocada | abierto |
| 2 | Cableado del SHT41 (GPIO8/9, 0x44, pull-ups, 100 kHz) | `sht41-wiring` | Montado en protoboard con Dupont y nunca observado: SDA y SCL pueden estar cruzados, puede faltar un pull-up o fallar un contacto | Escaneo I²C desde una imagen de prueba: ACK en 0x44 en GPIO8/9 a 100 kHz. Luego 3 lecturas con CRC válido y T entre 0 y 50 °C (contrato target de C-HW-04/05 y FR-SEN-01) | abierto |
| 3 | Corte de SDA por el operador | `sda-disconnect` | No hay conmutador. El corte lo hace el operador desconectando a mano el Dupont de SDA en la protoboard, y nunca se ha ensayado | Aviso bloqueante del banco «desconecta SDA» → la siguiente lectura sale inválida (CRC o NACK). Aviso «reconecta SDA» → la siguiente sale válida. La observación la hace el log del DUT, no el operador | abierto |
| 4 | Home Assistant de prueba | `home-assistant-test` | Todavía no existe. Falta decidir dónde corre: en el Pi del banco o en el PC con Docker | Instancia levantada con la integración MQTT apuntando al broker del banco. Se publica a mano una configuración `…/config` retained y HA crea la entidad; se borra al terminar | abierto — primero decidir dónde corre |
| 5 | Termohigrómetro de referencia | `reference-instrument` | Existe, junto con sobres de calibración de HR del 33 % y del 75 %, pero no se ha contrastado y no constan ni el modelo ni la tolerancia | Contraste con cada sobre hasta que la lectura se estabilice: el error en el 33 % y en el 75 % queda dentro de la tolerancia del fabricante. Se anotan el modelo, la tolerancia y los errores medidos en la capacidad | abierto |
| 6 | Pre-releases `ota-test-*` del repositorio | `github-test-releases` | No se han publicado: faltan la versión B, la imagen que no alcanza OPERATIVO, la imagen para otro chip y la imagen truncada (FSD §22.0) | `gh release list` muestra los tags `ota-test-*` marcados como pre-release, y `gh release view` lista el asset de cada una | abierto |
