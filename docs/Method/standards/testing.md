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

## Qué se aplica automáticamente

| Workflow | Cuándo | Comprueba |
|---|---|---|
| `host tests + secret scan` (`ci.yml`) | push a `main` y PR | Nivel host completo; gitleaks sobre el árbol y el historial; patrones de la instalación (secreto `NODO_DENYLIST`) |
| `Build Firmware` (`build.yml`) | push, tag `v*.*.*`, manual | Build en `espressif/idf:v6.0.2`; marcador de banco ausente en producción y presente en la imagen de banco; con un tag, el journey en el banco antes de publicar |
| `devcontainer image builds` | cambios en `.devcontainer/` | La imagen se construye con toolchain, pytest y runner |

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
por el portal con las credenciales del banco (`NODO_TEST_*` del entorno) y la
zona `zona1`; esperar `status` con `estado` = `online`. **Después:** el DUT está
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
asset de la imagen; publicar en `villa/zona1/<nodo>/cmd/ota` el payload
`{"url":"https://github.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/ota-test-<nombre>/<asset>"}`
sin retain. **Después:** el DUT vuelve a la imagen bajo prueba (OTA de vuelta o
flasheo) antes del test siguiente.

## P-NVS-ERASE — volver a PORTAL

**Necesita** bench-flash. Borrar la partición `nvs` (0x9000, 0x6000). El DUT
arranca en PORTAL (T02).
