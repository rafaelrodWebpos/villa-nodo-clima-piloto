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
