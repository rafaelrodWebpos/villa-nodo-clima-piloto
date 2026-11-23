# Estándar — Pruebas (portable)

Las pruebas forman parte del contrato de build. Cada regla de comportamiento
del FSD es verificable, y cada cambio trae el test que lo demuestra.

## Niveles

Las pruebas se ordenan por coste. Se usa el nivel más barato que pueda
detectar el fallo.

| Nivel | Dónde | Velocidad | Detecta |
|------|-------|-----------|---------|
| **host** | PC, compilador nativo | ms, cada commit | Lógica pura: parsing, codificación, cálculo, límites, transiciones. Sin hardware ni framework. |
| **target** | El ESP32-S3 real | segundos, antes del merge | Temporización de bus, NVS, servidor HTTP, comportamiento del RTOS. |
| **bench** | Dispositivo + pares reales | minutos, antes de la release | De extremo a extremo: recuperación, reconexión, tiempos reales. |

## Reglas

- **Toda regla Must/Should tiene un caso de prueba.** Una regla sin caso es un
  contrato sin probar y se muestra como hueco.
- **Todo cambio trae su test.** Los arreglos empiezan por el test de
  regresión, que debe fallar antes del arreglo.
- **Los casos citan los IDs de las reglas.** La cobertura se calcula, no se
  afirma, y nunca se mantiene a mano.
- **Las máquinas de estados se cubren por transición, no por estado.**
- **Sin huecos silenciosos.** Un caso especificado pero no construido se marca
  con su prerrequisito.
- **La suite está en verde antes del commit.**

## Pruebas de seguridad

Los casos se escriben para el perfil de amenazas del FSD (§19) y se basan en
OWASP ASVS / Top 10, CWE y NIST SP 800-115. Un criterio de seguridad tiene que
poder fallar: «cifrado u ofuscado» no puede fallar; «la contraseña marcador no
aparece en ninguna captura» sí.

## Matriz de fallos parciales (H-94, 2026-11-20)

Un plan que solo corta del todo el Wi-Fi, el broker o la alimentación deja sin
probar los fallos que más se ven en una casa. Antes de cerrar cada fase con red,
y antes de cada instalación, se recorre esta matriz contra el FSD. Para cada
fila se responde qué detecta el nodo, qué sigue funcionando, qué alerta sale (y
quién la emite) y cómo se recupera solo. Cada fila acaba con una prueba, con una
salvedad escrita o con una propuesta. El primer recorrido está en
`testing/analisis-cortes-parciales.md`.

| Familia | Fallos que hay que mirar | Cómo se simula en el banco |
|---|---|---|
| Internet parcial | Sin salida a Internet con la LAN arriba; DNS que no contesta o que da NXDOMAIN; pérdida de paquetes, retardo o cortes intermitentes; un servicio de nube caído con Internet arriba | `bench-ap-internet` (apagar la salida), `bench-sntp-block`, `bench-dns-override`; pérdida y DNS mudo: capacidades pendientes (CR-TB-23 a CR-TB-26) |
| Red parcial | AP o punto del mesh apagado; punto del mesh encendido sin enlace al resto; broker inalcanzable por DROP (no por RST); DHCP caído con el AP arriba; contrato DHCP que no se renueva; cambio a otra red | P-AP-OUTAGE, P-BROKER-OUTAGE; DROP y DHCP: capacidades pendientes; cambio de punto de acceso: solo en campo (una radio) |
| Energía parcial | Caídas breves y bajo voltaje (brownout); pérdida de una fase; un UPS que respalda unos equipos y otros no | Corte del USB-C con operador (`bench-operator-prompt`); bajo voltaje: solo con fuente regulable o en campo |
| Combinados | Orden de regreso tras un apagón (el nodo antes que el AP, el AP antes que el broker, Internet al final); bajo voltaje repetido mientras falla la red | Reset por la línea del banco con el AP y el broker apagados y levantados en orden (ejemplo: TC-CON-15) |

Reglas:

- **Las alertas son parte del caso.** Si el firmware no emite alertas, se dice
  quién las emite (por ejemplo, Home Assistant con el Last Will y los campos de
  diagnóstico) y se prueba ahí. Un fallo que nadie ve cuenta como hueco.
- **Sin el instrumento no hay verde.** Si el banco no puede simular un fallo, la
  fila queda como salvedad o como propuesta de capacidad (CR-TB del
  propietario). Nunca se da por probada con un fallo total parecido.
- **Total y parcial no son lo mismo.** Un broker parado (RST) y un broker que no
  contesta (DROP) ejercitan caminos distintos de TCP; se prueban por separado.

---

# Ejecutar una prueba

## Reglas para cualquier ejecución

- **Captura la evidencia antes de resetear nada**: un reset destruye el motivo
  del reset.
- **Un timeout es un fallo, no un resultado ausente.** Exige un marcador de
  finalización.
- **Una observación nula acusa primero al instrumento.** Antes de concluir algo
  de un silencio, muestra un **control positivo en la misma sesión**. En el
  ESP32-S3 (USB nativo), abrir el puerto serie con DTR/RTS activos detiene o
  resetea el chip: abre con ambas líneas en bajo.
- **Un experimento cuyo control no produce nada es nulo, no negativo.**
- **Usa la API del instrumento** del testbench antes que el acceso crudo.
- **Si la precondición falla, registra `not done`, nunca `failed`.**
- **Deja el banco como lo encontraste**: AP y broker activos, SNTP
  desbloqueado y SDA conectado.
- **Las credenciales del banco nunca entran en el repo.** Se leen de variables
  de entorno o del almacén de secretos del runner.
- **Se añaden las rutas una por una** (`git add <ruta>`), nunca `git add -A` ni
  `git add .`: la evidencia y las cachés que dejan los tests no entran sin revisarlas.

## Qué se aplica automáticamente

| Workflow | Cuándo | Comprueba |
|---|---|---|
| `host tests + secret scan` (`ci.yml`) | push a `main` y PR | Nivel host completo; gitleaks sobre el árbol y el historial; patrones de la instalación (secreto `NODO_DENYLIST`); `testing/test-plan.yaml` carga, con ids únicos y cada `needs` declarado (`scripts/ci/plan_check.py`) |
| `Build Firmware` (`build.yml`) | push, tag `v*.*.*`, manual | Build en `espressif/idf:v6.0.3`; marcador de banco ausente en producción y presente en la imagen de banco; con un tag, el journey en el banco antes de publicar |
| `devcontainer image builds` | cambios en `.devcontainer/` | La imagen se construye con toolchain, pytest y runner |
| `scripts/git-hooks/pre-push` (local; se activa con `git config core.hooksPath scripts/git-hooks`) | cada `git push` | gitleaks fijado (la misma versión que `ci.yml`) y los valores de `.env`, con el host de cada URL, sobre los commits que se suben; si encuentra algo, bloquea el push |
| `.claude/hooks/limite-espera.py` (H-62; hook PreToolUse de Claude Code) | cada comando Bash de la sesión de IA | Ninguna espera en segundo plano sin límite: bucle con sleep, `docker wait` o `tail --pid` con `timeout` ≤ 600 s. **Decisión del propietario (2026-11-23):** espera larga de hasta 93600 s (26 h) solo con `timeout N docker wait <contenedor>` o `timeout N bash -c 'while kill -0 <pid>; do sleep 60; done'`; lo demás sigue en 600 s. `gh run list -c` solo con el hash completo. Prueba: `tests/host/test_limite_espera.py` (CI) |

Los niveles target, bench, bench+ y field no los cubre ningún runner alojado.

---

# Procedimientos compartidos

Cada procedimiento indica las capacidades que necesita (`testing/test-plan.yaml`).
Los tests comparten la **preparación** a través de estos procedimientos, nunca
a través del orden de ejecución.

## P-BASE — DUT en la línea base operativa

**Necesita** bench-flash, bench-wifi-ap, bench-mqtt-broker, bench-portal-driver,
bench-serial-monitor. **Antes:** imagen de producción del commit bajo prueba
flasheada con los offsets de `flash_args`; NVS borrada. **Pasos:** aprovisionar
por el portal con las credenciales del banco (`NODO_TEST_*` del entorno), el
sitio `sitio1` y la zona `zona1`; esperar `status` con `estado` = `online`. **Después:** el DUT está
en OPERATIVO, el broker sin mensajes retained ajenos a la prueba y el log serie
capturado desde el arranque.

## P-AP-OUTAGE — corte del AP del banco

**Necesita** bench-wifi-ap-outage. **Pasos:** anotar la hora; apagar el AP;
mantenerlo apagado durante el tiempo del test; encenderlo y anotar la hora en
que vuelve a emitir balizas. **Después:** el AP queda activo aunque el test
falle (limpieza obligatoria).

## P-BROKER-OUTAGE — corte del broker del banco

**Necesita** bench-broker-outage. Igual que P-AP-OUTAGE, con el broker; se
anota la hora en que vuelve a aceptar conexiones. **Después:** broker activo y
sin los mensajes retained que dejó la prueba.

## P-SNTP-BLOCK — sin hora de red

**Necesita** bench-sntp-block. Bloquear UDP/123 hacia fuera antes de dar
alimentación al DUT. **Después:** desbloquear siempre.

## P-OTA-RELEASE — imagen de prueba en GitHub

**Necesita** github-test-releases y bench-ap-internet (bench+), o field-site
(field). **Pasos:** usar la pre-release `ota-test-<nombre>` del repo con el
asset de la imagen; publicar en `sitio1/zona1/<nodo>/cmd/ota` el payload
`{"url":"https://github.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/ota-test-<nombre>/<asset>"}`
sin retain. **Después:** el DUT vuelve a la imagen bajo prueba (OTA de vuelta o
flasheo) antes del test siguiente.

## P-BOOT-CAPTURE — capturar el arranque completo

**Necesita** bench-serial-monitor. `Init complete` y el marcador de banco se
emiten una sola vez por arranque, así que un monitor abierto después del
flasheo los pierde. **Pasos:** `POST /api/serial/reset` con el slot, sin sesión
de depuración. La respuesta trae el log de arranque como lista de líneas, y se
comprueba que `method` no sea `jtag`, porque entonces la respuesta es de
OpenOCD y no del DUT. Se busca el patrón en esas líneas. Si no aparece, se
lanza `POST /api/serial/monitor` con el patrón y un timeout de 15 s, y con ese
monitor ya esperando se repite el reset. **Después:** el log de arranque queda
guardado como evidencia del test.

## P-NVS-ERASE — volver a PORTAL

**Necesita** bench-flash. Borrar la partición `nvs` (0x9000, 0x6000). El DUT
arranca en PORTAL (T02).
