# Nodo Clima Piloto — Especificación Funcional (FSD)

```yaml
document_status: borrador — valores propuestos pendientes de aceptación (ver §4.4)
fsd_version: 0.1.0
repository: villa-nodo-clima-piloto (público)
baseline_commit: (commit que introduce este documento)
applicable_firmware_version: ninguna todavía
author: Rafael Rodriguez
reviewers: []
approval_status: no aprobado
created: 2026-10-11
last_updated: 2026-10-11
change_history:
  - 0.1.0 (2026-10-11): versión inicial; incluye sincronización SNTP (FR-TIME-*) y lista OTA
    verificada contra la cadena de redirección real de GitHub Releases.
superseded_requirements: []
open_decisions: ver §4.4 — cada entrada nombra los requisitos que bloquea
related_test_baseline: ninguna todavía (testing/test-plan.yaml, propiedad de /build)
```

## Convenciones de este documento

- **Identificadores estables** `FR-<ÁREA>-nn` (funcional), `NFR-<ÁREA>-nn`
  (calidad), `C-<ÁREA>-nn` (restricción) y `T-nn` (fila normativa de la tabla
  de transiciones). Un identificador no se renumera nunca: si un requisito
  queda obsoleto, se marca `deprecated` o `superseded`.
- **Prioridad**: `[Must]`, `[Should]` o `[May]`. Los requisitos se redactan con
  «deberá»; las restricciones, con «debe».
- **Procedencia**: `[user]` (lo dijo el usuario), `[derived]` (consecuencia
  lógica de un requisito `[user]`), `[pack:esp32]` (propuesto por el paquete
  ESP32 y aceptado por el usuario).
- **Estado**: un requisito es `aprobado` salvo que contenga un valor marcado
  **(propuesto)**. En ese caso queda `propuesto` hasta que se acepte el valor
  (§4.4). Ningún valor propuesto pasa a normativo de forma implícita.
- **Contratos de verificación**: cada Must/Should lleva su contrato. Se usa la
  forma compacta (tabla) salvo donde un aprobado erróneo es plausible
  (recuperación, rollback, ausencia de reinicios), donde se usa YAML completo.
  La columna **No debe ocurrir** es obligatoria.
- **Niveles de prueba**: `host` (lógica pura en el PC), `target` (el ESP32-S3
  real), `bench` (dispositivo con pares reales: AP Wi-Fi, broker, HA) y `other`
  (CI o revisión). Ver §22.0.

---

## 1. Visión general del sistema

### 1.1 Propósito

Nodo de sensado climático interior para una vivienda con Home Assistant. Un
ESP32-S3 mide temperatura y humedad relativa con un SHT41, calcula el punto de
rocío y publica las tres magnitudes por MQTT cada 60 s. Se configura sin
herramientas mediante un portal cautivo y se actualiza por OTA. Es un piloto:
valida el formato de tópicos y la robustez de conectividad que heredarán los
nodos posteriores.

### 1.2 Usuarios y partes interesadas

| Rol | Interacción |
|---|---|
| Instalador (el propietario) | Flashea el primer firmware, aprovisiona por el portal y lanza las OTA |
| Home Assistant | Consume los tópicos y la configuración de Discovery |
| Mantenedor (persona o agente IA) | Evoluciona el firmware contra este FSD |

### 1.3 Objetivos

- Publicar temperatura, humedad y punto de rocío cada 60 s, con el formato
  `{"v","u","ts"}` [user].
- Aparecer en Home Assistant sin configuración manual (MQTT Discovery) [user].
- Configurarse por portal cautivo, sin credenciales en el código [user].
- Sobrevivir a cortes de Wi-Fi y broker sin reiniciarse en bucle [user].
- Actualizarse por OTA con rollback automático [user].

### 1.4 No-objetivos

- Control de aire acondicionado por IR. Es una fase futura, no especificada
  aquí (§3.4) [user].
- Almacenar lecturas durante las desconexiones para reenviarlas después [user].
- Confidencialidad del tráfico MQTT en la LAN (sin TLS) [user].
- Funcionar a batería o con sueño profundo (assumed).

### 1.5 Flujo de alto nivel

```text
SHT41 ──I²C──▶ ESP32-S3 ──Wi-Fi/MQTT──▶ Broker (LAN) ──▶ Home Assistant
                  ▲                         │
                  │ HTTPS (OTA pull)        └── cmd/ota (URL) ──▶ nodo
            github.com (releases)
Teléfono ──Wi-Fi AP abierto──▶ portal cautivo (solo sin configuración)
```

---

## 2. Arquitectura del sistema

### 2.1 Arquitectura lógica

Un único firmware con cuatro flujos concurrentes: el **ciclo de medición**
(periódico, independiente de la conectividad), el **gestor de conectividad**
(máquina de estados, §6), el **publicador** (MQTT y Discovery) y el **gestor
OTA** (descarga bajo demanda). El ciclo de medición nunca espera a la red: si
el publicador no está conectado, la lectura se descarta (§5, FR-MED-06).

### 2.2 Plataforma hardware y restricciones que lee el build

| ID | Restricción | Procedencia |
|---|---|---|
| C-HW-01 [Must] | La placa debe ser una ESP32-S3-DevKitC-1 con módulo ESP32-S3-WROOM-1 **N8R8**: 8 MB de flash y 8 MB de PSRAM. | [user] |
| C-HW-02 [Must] | Una unidad con menos de 8 MB de flash no puede ejecutar este firmware; el build debe fijar `esptool` a 8 MB y no autodetectar. | [derived] |
| C-HW-03 [Must] | El firmware no debe requerir PSRAM; debe arrancar y funcionar con la PSRAM deshabilitada. | [derived] (propuesto: permite usar la variante N8) |
| C-HW-04 [Must] | El SHT41 debe conectarse por I²C a **SDA = GPIO8** y **SCL = GPIO9** **(propuesto)**, con alimentación de 3V3, en la dirección **0x44** (variante SHT41-AD1B). | [user] sensor; pines propuestos |
| C-HW-05 [Must] | El bus I²C debe operar a **100 kHz** **(propuesto)**, con resistencias pull-up en SDA y SCL (las del breakout o externas de 4,7–10 kΩ). | [derived] |
| C-HW-06 [Must] | La alimentación debe ser de 5 V por el USB de la DevKitC-1. | (assumed) |
| C-HW-07 [Must] | El firmware no debe usar GPIO0, GPIO3, GPIO45, GPIO46 (strapping), GPIO19/20 (USB) ni el LED RGB integrado (GPIO38/48, según revisión), para dejarlos libres de efectos de arranque. | [derived] |

**Tabla de particiones (normativa).** El build debe usar exactamente esta
tabla. Cualquier otra, incluida la que el toolchain aplica por defecto, es un
defecto.

| Nombre | Tipo | Subtipo | Offset | Tamaño |
|---|---|---|---|---|
| nvs | data | nvs | 0x9000 | 0x6000 (24 KB) |
| otadata | data | ota | 0xF000 | 0x2000 (8 KB) |
| phy_init | data | phy | 0x11000 | 0x1000 (4 KB) |
| ota_0 | app | ota_0 | 0x20000 | 0x300000 (3 MB) |
| ota_1 | app | ota_1 | 0x320000 | 0x300000 (3 MB) |

- **C-BLD-01** [Must] [derived] **(propuesto)**: la tabla de particiones debe
  ser la anterior; termina en 0x620000, dentro de los 8 MB.
- **C-BLD-02** [Must] [derived]: una imagen de aplicación mayor de 0x300000
  bytes (3 MB) no cabe en un slot OTA, y el build debe fallar si se supera.
- **C-BLD-03** [Must] [user]: el firmware debe construirse con **ESP-IDF 6.x**
  para el target `esp32s3`; la versión exacta se fija en el Method y en la CI.

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| C-HW-01, C-HW-02 | `esptool flash-id` sobre la placa del banco; inspeccionar la cabecera de la imagen de build | El chip informa de 8 MB; la cabecera declara un tamaño de flash de 8 MB | Cabecera con «detect» o con 4 MB | target + other (CI) |
| C-HW-03 | Build con la PSRAM deshabilitada; arrancar | Llega a T01 o T02 sin errores de memoria | Arranque fallido o un panic | target |
| C-HW-04, C-HW-05 | Escaneo del bus I²C desde el firmware de prueba | Responde 0x44 en GPIO8/9 a 100 kHz | Ningún ACK; otros pines configurados | target |
| C-HW-06 | Revisión del montaje | Alimentación por el USB de 5 V | — | other (revisión) |
| C-HW-07 | Revisión de las configuraciones de GPIO en el código (lista de pines usados) | Ningún pin de la lista prohibida | Uso de GPIO0/3/19/20/38/45/46/48 | other (revisión + CI con grep) |
| C-BLD-01 | `gen_esp32part.py` sobre la tabla de la imagen | Coincide fila a fila con la tabla de §2.2 | Tabla por defecto del toolchain | other (CI) |
| C-BLD-02 | Build de una imagen de 3 MB + 1 byte (prueba de la regla) | El build falla con un mensaje de tamaño | Que la imagen se genere | other (CI) |
| C-BLD-03 | Log de la CI | ESP-IDF v6.x, target esp32s3 | Otra versión mayor | other (CI) |

### 2.3 Arquitectura software

- Tareas FreeRTOS: medición, conectividad y publicación, y OTA (solo durante
  una descarga). La pila Wi-Fi, el cliente MQTT y el servidor HTTP del portal
  corren en las tareas propias de ESP-IDF.
- **Persistencia.** Solo la configuración (§17) en NVS y el estado de la imagen
  OTA en `otadata`. Contadores, backoff y estado de conexión son volátiles y se
  reinician en cada arranque.
- **Modelo de actualización.** Dos slots OTA con validación de la imagen nueva
  y rollback del bootloader (§12).

### 2.4 Capas de componentes

Dependencia estricta en un solo sentido: cada capa usa solo las que tiene
debajo. La frontera entre L0 y L1 es de propiedad: L1 es código propio
(drivers, handlers y codificadores); L0 son bibliotecas de ESP-IDF que se
configuran y usan, pero no se implementan.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ L2 Lógica de aplicación                                                  │
│   [Ciclo de medición + punto de rocío] [Gestor de conectividad] [Política OTA] │
├──────────────────────────────────────────────────────────────────────────┤
│ L1 Interfaces                                                            │
│   [Driver SHT41] [Publicador MQTT] [Discovery HA] [Portal cautivo]       │
│   [Receptor de comandos OTA]                                             │
├──────────────────────────────────────────────────────────────────────────┤
│ L0 Fundación                                                             │
│   [Wi-Fi STA/AP + DNS] [Cliente esp-mqtt] [esp_https_ota + bootloader]   │
│   [NVS] [SNTP] [Driver I²C maestro] [FreeRTOS + TWDT]                    │
└──────────────────────────────────────────────────────────────────────────┘
```

| Capa | Componente | Capítulo |
|---|---|---|
| L2 | Ciclo de medición y punto de rocío | §5 |
| L2 | Gestor de conectividad (máquina de estados) | §6 |
| L2 | Política OTA | §7 |
| L1 | Driver SHT41 | §8 |
| L1 | Publicador MQTT | §9 |
| L1 | Discovery de Home Assistant | §10 |
| L1 | Portal cautivo | §11 |
| L1 | Receptor de comandos OTA | §12 |
| L0 | Wi-Fi, DNS, MQTT, HTTPS OTA, NVS, SNTP, I²C, FreeRTOS/TWDT | §13–§15 |

La correspondencia de estas capas con el código fuente es HOW y está en
`docs/Method/project/arquitectura.md`.

---

## 3. Fases de implementación

Cada fase se entra solo con lo que entregaron las anteriores.

### 3.1 Fase 1 — Fundación: medir y aprovisionar

- **Alcance.** Driver SHT41, ciclo de medición, punto de rocío, identidad,
  configuración en NVS, portal cautivo, Wi-Fi STA con backoff, SNTP y tabla de
  particiones.
- **Entregables.** Un firmware que, sin configuración, abre el portal; una vez
  aprobado, se une al Wi-Fi y registra las tres medidas por consola serie cada
  60 s.
- **Criterios de salida.** Pasan FR-SEN-01, FR-SEN-02, FR-MED-03…05, FR-ID-01,
  FR-POR-*, FR-CFG-01 (fila de cortes de alimentación), FR-CON-02, FR-CON-06,
  NFR-SEC-01, C-CFG-01 y las filas T01–T07, T09 y T10. Todo se verifica por
  host, target, log serie y escaneo Wi-Fi; nada requiere MQTT.
- **Dependencias.** Hardware (DevKitC-1 N8R8 y SHT41) y el harness del
  proyecto (`/harness`). No depende de ninguna fase anterior.

### 3.2 Fase 2 — Telemetría: MQTT y Home Assistant

- **Alcance.** Publicador MQTT, LWT, `status` con diagnóstico, Discovery,
  recuperación de broker y Wi-Fi, watchdog y ausencia de reinicios por
  conectividad.
- **Entregables.** Las tres entidades aparecen en Home Assistant y se recuperan
  solas tras cortes.
- **Criterios de salida.** Pasan FR-MQTT-01…08, FR-HA-*, FR-MED-01, -02 y -06,
  FR-SEN-03, NFR-SEN-01, FR-CON-01, -03, -04 y -05, FR-TIME-*, NFR-WDT-01,
  FR-SEC-03 y las filas T08 y T11–T16.
- **Dependencias.** Fase 1: la configuración del broker llega por el portal y
  la conexión, por el Wi-Fi de la Fase 1.

### 3.3 Fase 3 — Actualización OTA

- **Alcance.** Receptor de comandos OTA, política de hosts, descarga HTTPS,
  validación de imagen y rollback.
- **Entregables.** Actualización desde una release de GitHub con un comando
  MQTT, y rollback automático si la imagen nueva no alcanza OPERATIVO.
- **Criterios de salida.** Pasan FR-OTA-*, NFR-OTA-01, FR-MQTT-09, NFR-SEC-02,
  FR-CFG-01 (fila de OTA) y las filas T17–T23.
- **Dependencias.** Fase 2, porque el comando llega por MQTT y la validación de
  la imagen exige alcanzar OPERATIVO. Además, al menos una release publicada en
  GitHub con una versión distinta a la instalada, que la CI del proyecto
  (`/harness`, setup-action) produce.

### 3.4 Fase futura — Emisor IR (no especificada)

El control de un aire acondicionado por IR se especificará con un delta de
este FSD (`/define update`). Nada de este documento lo presupone. No hay pines
reservados ni tópicos de comando definidos para él.

---

## 4. Riesgos, supuestos y dependencias

### 4.1 Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|---|---|---|---|
| El autocalentamiento de la placa sesga la temperatura | Alta | Medio | Montar el SHT41 separado de la DevKitC-1 (manual §2); NFR-SEN-01 lo detecta |
| Al pasar el AP al canal del router durante la prueba de unión, el teléfono se desconecta y no ve la página de resultado | Media | Bajo | Si la unión tiene éxito, el AP desaparece y el nodo reinicia, lo que ya indica éxito; si falla, el AP sigue y la página de error se ve al recargar (§11) |
| GitHub cambia los hosts de redirección de los assets de release (ya migró de `objects.` a `release-assets.githubusercontent.com`) | Media | Medio | La OTA se rechaza de forma segura con `rechazado:host` (FR-OTA-02), lo que hace visible el cambio; la lista se amplía con un delta del FSD y se flashea por USB una vez |
| Una cuenta de GitHub comprometida publica un firmware malicioso | Baja | Alto | Riesgo aceptado: no hay firma de imagen (§19) |
| Un atacante en la LAN lee las credenciales MQTT o falsea medidas | Media | Bajo | Riesgo aceptado: MQTT sin TLS en la LAN [user] |
| Una configuración de broker errónea deja el nodo reintentando para siempre | Media | Medio | El diagnóstico del broker lo muestra ausente; se reaprovisiona borrando la NVS por USB (manual) |
| Sin acceso a Internet no hay SNTP | Baja | Bajo | Se publica con `ts: null` y `hora_valida: false` (FR-TIME-03, §9.3); la medición y la publicación no se detienen (FR-TIME-05) |
| Tras una OTA con el Wi-Fi caído, una imagen buena se revierte por no validarse a tiempo | Baja | Bajo | Se reintenta la OTA cuando vuelva el Wi-Fi |

### 4.2 Supuestos

- La LAN doméstica tiene un broker MQTT accesible por usuario y contraseña en
  un puerto TCP sin TLS (por defecto 1883) [user].
- Home Assistant usa el prefijo de Discovery `homeassistant` (assumed: es el
  valor por defecto de HA).
- El router Wi-Fi es de 2,4 GHz, WPA2-PSK o abierto (assumed: el ESP32-S3 no
  soporta 5 GHz).
- La LAN tiene salida a Internet para SNTP y para descargar desde GitHub
  (assumed).

### 4.3 Explícitamente fuera de alcance

| Elemento | Origen |
|---|---|
| Buffer de lecturas offline (en RAM o flash) y reenvío | Rechazado por el usuario |
| OTA push (endpoint HTTP en el nodo) | Rechazado por el usuario |
| TLS hacia el broker | Rechazado por el usuario; riesgo aceptado |
| Secure Boot v2 y firma de imagen | Rechazado por el usuario; riesgo aceptado |
| Cifrado de flash/NVS | No justificado por el perfil (§19); riesgo aceptado |
| Botón BOOT para reabrir el portal con el nodo configurado | Propuesto por pack:esp32, no aceptado. Para reaprovisionar se borra la NVS por USB |
| Log por UDP | Propuesto por pack:esp32, no aceptado |
| Emisor IR para aire acondicionado | Fase futura [user] |

### 4.4 Decisiones abiertas — valores propuestos pendientes de aceptación

Cada valor está marcado **(propuesto)** en el texto. Hasta que se acepte, el
requisito que lo contiene queda en estado `propuesto`.

| # | Valor propuesto | Requisitos que bloquea |
|---|---|---|
| D1 | Pines I²C SDA=GPIO8, SCL=GPIO9; 100 kHz | C-HW-04, C-HW-05 |
| D2 | Tabla de particiones de §2.2 | C-BLD-01 |
| D3 | Tolerancia del periodo: 60 s ± 1 s | FR-MED-01 |
| D4 | Redondeo a 1 decimal en las tres medidas | FR-MED-05 |
| D5 | Nombres de medida `temperatura`, `humedad`, `punto_rocio`; unidades `°C`, `%`, `°C` | FR-MQTT-01, FR-MQTT-02 |
| D6 | `ts` en segundos Unix UTC del instante de medida; servidor `pool.ntp.org`; primera sincronización ≤ 30 s; resincronización cada 1 h. La regla de `null` y la prohibición de 1970 son [user], no propuestas | FR-MQTT-03, FR-TIME-01, FR-TIME-04 |
| D7 | Medidas retained con QoS 0; `status` retained con QoS 1; keepalive 60 s | FR-MQTT-04, FR-MQTT-05 |
| D8 | Backoff 1 s ×2 hasta un techo de 60 s | FR-CON-02 |
| D9 | Plazos: arranque → 1.ª publicación ≤ 30 s; vuelta del Wi-Fi → ≤ 90 s; vuelta del broker → ≤ 75 s | FR-CON-03, -04, -05 |
| D10 | Identificador `clima-` + 3 últimos bytes de la MAC STA | FR-ID-01 |
| D11 | Validación de campos del portal (§17) y regex de zona `^[a-z0-9_-]{1,32}$` | FR-POR-04 |
| D12 | Prueba de unión del portal ≤ 20 s; reinicio tras guardar ≤ 5 s | FR-POR-05, FR-POR-06 |
| D13 | `expire_after` = 180 s en Discovery | FR-HA-03 |
| D14 | Hosts OTA permitidos: `github.com` y `release-assets.githubusercontent.com` (verificados contra la cadena real, §7.3); máximo 3 redirecciones | FR-OTA-02 |
| D19 | Restringir la URL inicial a `https://github.com/{{ota_repo}}/releases/download/`, con `{{ota_repo}}` = `<owner>/villa-nodo-clima-piloto` fijado en el build | FR-OTA-11 |
| D15 | Validación de imagen nueva ≤ 300 s; versión nueva visible ≤ 120 s | FR-OTA-06, FR-OTA-07 |
| D16 | Timeout del watchdog de tareas: 30 s | NFR-WDT-01 |
| D17 | Exactitud frente a referencia: ± 0,5 °C y ± 3 %HR | NFR-SEN-01 |
| D18 | Campos y periodo del diagnóstico en `status` (§9.3) | FR-MQTT-08 |
| D20 | Valor de `{{ota_repo}}`: el dueño del repositorio en GitHub. Es público y no identifica el lugar de instalación | FR-OTA-11 |

---

# Parte A — Lógica de aplicación (L2)

## 5. Ciclo de medición y punto de rocío

### 5.1 Propósito

Disparar una lectura del SHT41 cada 60 s, calcular el punto de rocío y
entregar las medidas válidas al publicador. Funciona en todos los estados de
conectividad salvo ARRANQUE (§6).

### 5.2 Requisitos

- **FR-MED-01** [Must] [user]: el nodo deberá iniciar un ciclo de medición
  cada 60 s **± 1 s (propuesto)**, medidos con reloj monotónico e
  independientemente del estado de conectividad.
- **FR-MED-02** [Must] [user]: el nodo deberá ejecutar el ciclo de medición en
  los estados PORTAL, VALIDANDO, CONECTANDO_WIFI, CONECTANDO_BROKER, OPERATIVO
  y OTA_DESCARGA; la evidencia es el contador `lecturas` del diagnóstico
  (§9.3).
- **FR-MED-03** [Must] [user]: el nodo deberá calcular el punto de rocío con
  la fórmula de Magnus (constantes de Sonntag, §5.4) con un error ≤ 0,1 °C
  respecto a la fórmula de referencia en doble precisión, para T ∈ [−10, 50] °C
  y HR ∈ [1, 100] %.
- **FR-MED-04** [Must] [derived]: el nodo no deberá publicar el punto de rocío
  de un ciclo en el que la temperatura o la humedad sean inválidas (FR-SEN-02),
  o en el que la HR sea ≤ 0 %.
- **FR-MED-05** [Must] [derived]: el campo `v` deberá redondearse a **1
  decimal (propuesto)**, alejando de cero los empates.
- **FR-MED-06** [Must] [user]: una lectura tomada mientras el nodo no está en
  OPERATIVO no deberá publicarse nunca; al entrar en OPERATIVO, solo se
  publicará la lectura válida más reciente de cada medida.

### 5.3 Contratos de verificación

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-MED-01 | OPERATIVO; capturar 11 mensajes consecutivos de `temperatura` | Los 10 intervalos entre llegadas están en [59, 61] s | Deriva acumulada > 2 s en 10 ciclos; dos publicaciones en el mismo ciclo | bench |
| FR-MED-02 | Broker detenido 10 min | Al volver, `lecturas` ha aumentado entre 9 y 11 respecto a su valor previo | `lecturas` sin cambio; reinicio del nodo (uptime menor) | bench |
| FR-MED-03 | Tabla de 200 pares (T, HR) en la rejilla del rango, incluidos los extremos | \|Td − Td_ref\| ≤ 0,1 °C en todos | NaN o infinito para HR ∈ [1, 100] | host |
| FR-MED-04 | Entrada con HR = 0 y entrada con T inválida | La salida es «no publicar punto_rocio» | Que se publique punto_rocio con 0, NaN, −273 o el valor anterior | host |
| FR-MED-05 | Valores 21,45 · −0,05 · 21,449 · 99,96 | 21,5 · −0,1 · 21,4 · 100,0 | Más de 1 decimal en el JSON; `v` como string | host |
| FR-MED-06 | Broker detenido 5 min; luego se restablece; suscriptor en `villa/#` con retained descartados | Tras reconectar llega exactamente 1 mensaje por medida, con `ts` ≤ 60 s anterior a la llegada | Ráfaga de mensajes con `ts` de la ventana sin conexión | bench |

### 5.4 Algoritmo

```text
γ(T, HR) = ln(HR/100) + (b·T)/(c + T)      b = 17.62, c = 243.12 °C
Td       = c·γ / (b − γ)
```

Cada ciclo: leer el SHT41 → si la lectura es válida, calcular Td → redondear
→ si el estado es OPERATIVO, publicar `temperatura`, `humedad` y `punto_rocio`,
en ese orden; si no, descartar → incrementar `lecturas` si la lectura fue
válida, o `err_sensor` si no lo fue.

## 6. Gestor de conectividad (máquina de estados)

### 6.1 Propósito

Llevar el nodo del arranque a OPERATIVO y mantenerlo ahí, recuperándose de
pérdidas de Wi-Fi y de broker **sin reiniciarse** [user].

### 6.2 Estados

| Estado | Significado | Persistente |
|---|---|---|
| ARRANQUE | Inicialización; dura hasta leer la NVS | No |
| PORTAL | Sin configuración válida; el AP y el portal están activos | No (se deriva de la NVS) |
| VALIDANDO | El portal recibió un formulario válido; el nodo prueba la unión STA | No |
| CONECTANDO_WIFI | Configurado; el STA se intenta unir con backoff | No |
| CONECTANDO_BROKER | Wi-Fi con IP; el cliente MQTT se intenta conectar con backoff | No |
| OPERATIVO | MQTT conectado; se publican las medidas | No |
| OTA_DESCARGA | Descarga y escritura de una imagen en curso | No |

Región ortogonal **Validación de imagen**: `PENDIENTE` (primer arranque de una
imagen recién instalada) → `VÁLIDA`. Su estado persiste en `otadata`.

### 6.3 Tabla de transiciones (normativa)

Todas las filas son requisitos [Must]. Procedencia: [user] para la ausencia de
reinicios y los reintentos; [derived] para el resto. Los plazos marcados
**(propuesto)** dependen de §4.4.

| ID | Estado | Evento | Guarda | Siguiente | Acción | Límite | No debe ocurrir |
|---|---|---|---|---|---|---|---|
| T01 | ARRANQUE | fin_arranque | Configuración válida en NVS | CONECTANDO_WIFI | Arrancar el STA y el ciclo de medición | 2 s (propuesto) | Abrir el AP |
| T02 | ARRANQUE | fin_arranque | No hay configuración válida | PORTAL | Arrancar el AP, el DNS, el HTTP y el ciclo de medición | 10 s (propuesto) | Intentar el STA |
| T03 | PORTAL | envío | Algún campo inválido (§17) | PORTAL | Responder con un error por campo | 1 s | Escribir en la NVS |
| T04 | PORTAL | envío | Todos los campos válidos | VALIDANDO | Probar la unión STA (AP+STA) con los datos del formulario | — | Escribir en la NVS |
| T05 | VALIDANDO | wifi_up | — | ARRANQUE (reinicio) | Persistir la configuración, responder con éxito y reiniciar | 5 s (propuesto) | Reiniciar sin haber persistido |
| T06 | VALIDANDO | wifi_down o 20 s sin IP | — | PORTAL | Responder «no se pudo conectar» y descartar los datos | 20 s (propuesto) | Persistir; apagar el AP |
| T07 | VALIDANDO | envío | — | VALIDANDO | Responder «ocupado» | 1 s | Iniciar una segunda prueba |
| T08 | CONECTANDO_WIFI | wifi_up | — | CONECTANDO_BROKER | Reiniciar el backoff de Wi-Fi; arrancar SNTP y el cliente MQTT | 1 s | — |
| T09 | CONECTANDO_WIFI | wifi_down (intento fallido) | — | CONECTANDO_WIFI | Programar un reintento con el backoff (FR-CON-02) | — | Reiniciar el nodo; abrir el AP |
| T10 | CONECTANDO_WIFI | backoff | — | CONECTANDO_WIFI | Lanzar un intento de unión | — | — |
| T11 | CONECTANDO_BROKER | mqtt_up | — | OPERATIVO | Publicar `status` online, luego Discovery, luego las medidas más recientes; reiniciar el backoff MQTT; si la imagen está PENDIENTE, marcarla VÁLIDA | 5 s | Publicar medidas antes que `status` |
| T12 | CONECTANDO_BROKER | mqtt_down (intento fallido) | — | CONECTANDO_BROKER | Programar un reintento con el backoff | — | Reiniciar el nodo; desconectar el Wi-Fi |
| T13 | CONECTANDO_BROKER | backoff | — | CONECTANDO_BROKER | Lanzar un intento de conexión MQTT | — | — |
| T14 | CONECTANDO_BROKER | wifi_down | — | CONECTANDO_WIFI | Detener los intentos MQTT; programar un reintento Wi-Fi | 1 s | Reiniciar el nodo |
| T15 | OPERATIVO | mqtt_down | — | CONECTANDO_BROKER | Programar un reintento MQTT | 1 s | Reiniciar el nodo; desconectar el Wi-Fi |
| T16 | OPERATIVO | wifi_down | — | CONECTANDO_WIFI | Programar un reintento Wi-Fi | 1 s | Reiniciar el nodo |
| T17 | OPERATIVO | cmd_ota | Cumple FR-OTA-02…05 (no retained) | OTA_DESCARGA | Iniciar la descarga; diagnóstico `ota` = `en_curso` | 2 s | — |
| T18 | OPERATIVO | cmd_ota | Incumple alguna regla de §7 | OPERATIVO | Publicar `status` con `ota` = `rechazado:<motivo>` | 2 s | Descargar; cambiar de partición |
| T19 | OTA_DESCARGA | ota_ok | — | ARRANQUE (reinicio) | Publicar `status` con `ota` = `ok`, publicar `offline` y reiniciar en el nuevo slot | 5 s | Reiniciar sin cambiar de slot |
| T20 | OTA_DESCARGA | ota_err | — | OPERATIVO | Publicar `status` con `ota` = `error:<motivo>`; conservar la imagen en ejecución | 2 s | Reiniciar; marcar el slot nuevo como arrancable |
| T21 | OTA_DESCARGA | cmd_ota | — | OTA_DESCARGA | Publicar `ota` = `rechazado:ocupado` | 2 s | Abortar o reiniciar la descarga en curso |
| T22 | OTA_DESCARGA | mqtt_down o wifi_down | — | CONECTANDO_BROKER o CONECTANDO_WIFI, según el evento | Abortar la descarga; conservar la imagen en ejecución | 2 s | Reiniciar; activar una imagen parcial |
| T23 | (Validación) PENDIENTE | 300 s sin T11 desde el arranque | — | Reinicio → rollback | Reiniciar; el bootloader arranca la imagen anterior | 300 s (propuesto) | Seguir con la imagen no validada |

**Acciones globales.** Si salta el watchdog de tareas (NFR-WDT-01), el nodo se
reinicia desde cualquier estado. Es el único reinicio no ordenado por T05, T19
o T23.

### 6.4 Completitud (estado × evento)

`Tnn` = la fila que lo trata · `ign` = se ignora y se registra a nivel debug ·
`imp` = imposible por construcción (motivo al pie).

| Estado \ Evento | fin_arranque | envío | wifi_up | wifi_down | backoff | mqtt_up | mqtt_down | cmd_ota | ota_ok/err |
|---|---|---|---|---|---|---|---|---|---|
| ARRANQUE | T01/T02 | imp¹ | imp² | imp² | imp³ | imp⁴ | imp⁴ | imp⁴ | imp⁵ |
| PORTAL | imp⁶ | T03/T04 | imp² | imp² | imp³ | imp⁴ | imp⁴ | imp⁴ | imp⁵ |
| VALIDANDO | imp⁶ | T07 | T05 | T06 | imp³ | imp⁴ | imp⁴ | imp⁴ | imp⁵ |
| CONECTANDO_WIFI | imp⁶ | imp¹ | T08 | T09 | T10 | imp⁴ | imp⁴ | imp⁴ | imp⁵ |
| CONECTANDO_BROKER | imp⁶ | imp¹ | ign | T14 | T13 | T11 | T12 | imp⁴ | imp⁵ |
| OPERATIVO | imp⁶ | imp¹ | ign | T16 | ign⁷ | ign | T15 | T17/T18 | imp⁵ |
| OTA_DESCARGA | imp⁶ | imp¹ | ign | T22 | ign⁷ | ign | T22 | T21 | T19/T20 |

¹ El servidor HTTP del portal solo existe en PORTAL y VALIDANDO.
² El STA no está iniciado. ³ No hay temporizador de backoff armado.
⁴ El cliente MQTT no está conectado; no se pueden recibir comandos.
⁵ No hay descarga en curso. ⁶ Se emite una sola vez por arranque.
⁷ Un temporizador residual se cancela al entrar en OPERATIVO; si dispara, se
ignora.

### 6.5 Requisitos adicionales de conectividad

- **FR-CON-01** [Must] [user]: el nodo no deberá ejecutar ningún reinicio por
  software a causa de la pérdida del Wi-Fi o del broker, sea cual sea la
  duración de la pérdida.
- **FR-CON-02** [Must] [user]: los reintentos de Wi-Fi y de MQTT deberán seguir
  un backoff exponencial que empieza en **1 s, se duplica en cada fallo y tiene
  un techo de 60 s (propuesto)**, y que vuelve a 1 s tras cada conexión
  lograda.
- **FR-CON-03** [Must] [user]: después de que el AP Wi-Fi vuelva a estar
  disponible, el nodo deberá publicar una medida válida en ≤ **90 s
  (propuesto)**.
- **FR-CON-04** [Must] [user]: después de que el broker vuelva a estar
  disponible, el nodo deberá publicar una medida válida en ≤ **75 s
  (propuesto)**, sin desasociarse del Wi-Fi.
- **FR-CON-05** [Must] [derived]: desde el encendido de un nodo configurado,
  con Wi-Fi y broker disponibles, la primera medida válida deberá llegar al
  broker en ≤ **30 s (propuesto)**.
- **FR-CON-06** [Must] [derived]: un nodo configurado no deberá volver a PORTAL
  por fallos de conexión; solo vuelve a PORTAL si la NVS no contiene una
  configuración válida.

### 6.6 Contratos de verificación

```yaml
id: FR-CON-01
verification:
  preconditions:
    - DUT en OPERATIVO, con uptime y motivo de reset conocidos (diagnóstico).
  stimulus:
    - Caso A — apagar el AP Wi-Fi durante 60 min y volver a encenderlo.
    - Caso B — detener el broker durante 60 min (Wi-Fi activo) y volver a arrancarlo.
  expected_observations:
    - En el primer `status` tras la recuperación, `uptime_s` ≥ duración del corte.
    - El motivo de reset (`reset`) no cambia respecto al previo al corte.
    - La consola serie no muestra ningún banner de arranque durante el corte.
  timing: ventana de observación = corte + 120 s
  tolerance: ninguna — un solo reinicio es un fallo
  prohibited_outcomes:
    - Cualquier reinicio (banner de arranque, uptime menor, `reset` = sw/panic/task_wdt).
    - Apertura del AP del portal.
    - Necesidad de reaprovisionar.
  tier: bench
  evidence:
    - Instantes de corte y restablecimiento.
    - Log serie completo de la ventana.
    - `status` previo y posterior.
  cleanup:
    - AP y broker activos; DUT en OPERATIVO.
```

```yaml
id: FR-CON-03
verification:
  preconditions:
    - DUT en OPERATIVO; suscriptor en villa/<zona>/<nodo>/# sin retained.
  stimulus:
    - Apagar el AP Wi-Fi 5 min (el backoff llega al techo); encender el AP.
  expected_observations:
    - Llega un mensaje válido de `temperatura` (JSON conforme a FR-MQTT-02).
    - Su `ts` es posterior al restablecimiento del AP.
  timing: ≤ 90 s desde que el AP emite balizas hasta el mensaje
  tolerance: +5 s (arranque del AP del banco)
  prohibited_outcomes:
    - Reinicio del DUT (uptime menor en `status`).
    - Que la «recuperación» sea un mensaje retained antiguo.
    - Apertura del portal.
  tier: bench
  evidence: [instantes AP off/on, primer mensaje con su hora de llegada, status posterior]
  cleanup: [AP activo, DUT en OPERATIVO]
```

```yaml
id: FR-CON-04
verification:
  preconditions:
    - DUT en OPERATIVO; Wi-Fi estable.
  stimulus:
    - Detener el broker 5 min; arrancarlo.
  expected_observations:
    - Llega un mensaje válido de medida no retained con `ts` posterior al arranque del broker.
    - `rssi` aparece en el `status` posterior y la asociación Wi-Fi no se perdió (log sin desasociación).
  timing: ≤ 75 s desde que el broker acepta conexiones
  tolerance: +5 s
  prohibited_outcomes:
    - Reinicio del DUT.
    - Desasociación del Wi-Fi provocada por el nodo.
    - Ráfaga de lecturas de la ventana sin conexión (viola FR-MED-06).
  tier: bench
  evidence: [instantes de stop/start del broker, primer mensaje, log serie]
  cleanup: [broker activo]
```

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-CON-02 | Función de backoff alimentada con 10 fallos y luego un éxito | 1, 2, 4, 8, 16, 32, 60, 60, 60, 60 s; tras el éxito, 1 s | Superar 60 s; no reiniciar a 1 s | host |
| FR-CON-02 | AP apagado 5 min; marcas de tiempo de los intentos en el log | Intervalos dentro de ±10 % de la secuencia | Intentos en ráfaga (< 1 s) | bench |
| FR-CON-05 | Cortar y devolver la alimentación a un DUT configurado | Primera medida en ≤ 30 s | Que pase por PORTAL | bench |
| FR-CON-06 | Configurar con un SSID que deja de existir; esperar 15 min | El DUT sigue en CONECTANDO_WIFI; el AP del portal no aparece en el escaneo | AP `clima-*` visible | bench |
| T01–T23 | Una prueba por fila: forzar el estado de origen, inyectar el evento y comprobar la guarda | Estado siguiente y acción observables (log de transición, §9.3) dentro del límite | Lo indicado en la columna «No debe ocurrir» | host (lógica de la tabla) + bench (filas con Wi-Fi/MQTT reales) |

## 7. Política OTA

### 7.1 Propósito

Decidir si un comando OTA se acepta y gobernar el ciclo descarga → validación →
reinicio → confirmación o rollback. La política es una función pura (URL,
estado, versión → aceptar o rechazar con motivo) que se prueba en host.

### 7.2 Requisitos

- **FR-OTA-02** [Must] [user]: el nodo deberá rechazar con `rechazado:host`
  toda URL que no empiece por `https://` o cuyo host no esté en la lista
  permitida — **`github.com` y `release-assets.githubusercontent.com`
  (propuesto)** —, y deberá aplicar la misma regla a cada redirección HTTP,
  con un máximo de **3 redirecciones (propuesto)**; la siguiente se aborta con
  `error:redirecciones`.
- **FR-OTA-11** [Must] [derived] **(propuesto)**: el nodo deberá rechazar con
  `rechazado:ruta` toda URL inicial que no empiece por
  `https://github.com/{{ota_repo}}/releases/download/`. Sin esta regla, el host
  `github.com` permitiría instalar la release de cualquier cuenta de GitHub
  desde un comando enviado por la LAN.
- **FR-OTA-03** [Must] [derived]: el nodo deberá abortar con `error:tls`
  cualquier descarga cuyo certificado de servidor no verifique contra el
  bundle de CAs del firmware.
- **FR-OTA-04** [Must] [derived]: el nodo deberá ignorar, sin actuar y con
  registro, todo mensaje de comando OTA entregado con el flag retain.
- **FR-OTA-05** [Must] [derived]: el nodo deberá rechazar con `error:imagen`
  una imagen que no sea una aplicación ESP-IDF válida para `esp32s3` (cabecera,
  chip o SHA-256), y con `rechazado:misma_version` una cuya versión coincida
  con la que está en ejecución.
- **FR-OTA-06** [Must] [user]: tras una descarga válida, el nodo deberá
  reiniciar en la imagen nueva y publicar su versión en el campo `fw` de
  `status` en ≤ **120 s (propuesto)** desde el final de la descarga.
- **FR-OTA-07** [Must] [user]: si la imagen nueva no alcanza OPERATIVO en ≤
  **300 s (propuesto)** desde su primer arranque, el nodo deberá volver a la
  imagen anterior.
- **FR-OTA-08** [Must] [derived]: una pérdida de Wi-Fi o de MQTT durante la
  descarga deberá abortarla sin reiniciar y sin cambiar la imagen arrancable.
- **FR-OTA-10** [Must] [derived]: un comando OTA recibido durante una descarga
  deberá rechazarse con `rechazado:ocupado`, sin afectar a la descarga en
  curso.
- **NFR-OTA-01** [Should] [derived]: durante una descarga, los ciclos de
  medición deberán mantener un periodo de 60 s ± 5 s.

### 7.3 Cadena de redirección de GitHub Releases (base de FR-OTA-02)

Comprobada con peticiones reales a assets públicos de GitHub Releases:

| URL pedida | Respuesta | Destino |
|---|---|---|
| `https://github.com/<o>/<r>/releases/download/<tag>/<asset>` | 302 | `https://release-assets.githubusercontent.com/github-production-release-asset/…` (URL firmada y temporal) |
| `https://github.com/<o>/<r>/releases/latest/download/<asset>` | 302 | `https://github.com/<o>/<r>/releases/download/<tag-actual>/<asset>` y, desde ahí, como en la fila anterior |
| `https://release-assets.githubusercontent.com/…` | 200 | Contenido del asset (fin de la cadena) |

Por tanto, la lista permitida cubre ambas formas de URL con 1 o 2 saltos, por
debajo del límite de 3. `objects.githubusercontent.com` no aparece en la
cadena y no se permite. La URL firmada caduca en minutos, así que el comando
debe llevar la URL de `github.com`, nunca la de `release-assets` copiada.

### 7.4 Contratos de verificación

```yaml
id: FR-OTA-07
verification:
  preconditions:
    - DUT en OPERATIVO con la versión A.
    - Release de prueba con la versión B construida para no alcanzar OPERATIVO
      (p. ej., con el host del broker forzado a uno inexistente).
  stimulus:
    - Publicar el comando OTA con la URL de B.
  expected_observations:
    - El DUT descarga B y reinicia en B (banner de B por serie).
    - En ≤ 300 s, el DUT reinicia y arranca A.
    - El primer `status` tras la vuelta muestra `fw` = A.
  timing: ≤ 300 s desde el primer arranque de B hasta el reinicio de rollback
  tolerance: +10 s
  prohibited_outcomes:
    - Que el DUT quede en B sin publicar.
    - Bucle de reinicios entre A y B (más de un rollback).
    - Necesidad de flasheo por USB para recuperarlo.
  tier: bench
  evidence: [log serie con ambos banners, instantes, status final]
  cleanup: [DUT en A, OPERATIVO]
```

```yaml
id: FR-OTA-08
verification:
  preconditions:
    - DUT en OPERATIVO con la versión A; release B válida de ≥ 1 MB.
  stimulus:
    - Publicar el comando OTA de B; cuando el log indique ≥ 30 % descargado,
      apagar el AP Wi-Fi 30 s y volver a encenderlo.
  expected_observations:
    - El log registra el aborto de la descarga.
    - Tras la recuperación, `status` muestra `fw` = A y `ota` = `error:<motivo>`.
  timing: recuperación conforme a FR-CON-03
  tolerance: —
  prohibited_outcomes:
    - Reinicio del DUT.
    - Arranque de una imagen parcial o de B.
    - `otadata` apuntando a la partición escrita a medias.
  tier: bench
  evidence: [log serie, status final, uptime antes y después]
  cleanup: [AP activo; DUT en A]
```

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-OTA-02 | Política con `http://github.com/x`, `https://evil.example/x`, `https://github.com/x` → redirección a `objects.githubusercontent.com`, y una cadena de 4 redirecciones | `rechazado:host` en las tres primeras; `error:redirecciones` en la cuarta | Aceptar alguna; descargar algún byte de un host no permitido | host (política) |
| FR-OTA-02 | Comando con la URL `releases/download/<tag>/` real del repo y otro con `releases/latest/download/` | Ambas descargas se completan (1 y 2 saltos) | `rechazado:host` en una URL legítima | bench |
| FR-OTA-11 | Política con `https://github.com/otro/repo/releases/download/v1/x.bin` y `https://github.com/{{ota_repo}}/archive/x` | `rechazado:ruta` en ambas | Descargar la release de otra cuenta | host |
| FR-OTA-03 | URL a un servidor permitido con un certificado autofirmado (DNS del banco) | `ota` = `error:tls` | Escritura en el slot inactivo | bench |
| FR-OTA-04 | Publicar el comando OTA con retain y reconectar el DUT | Sin descarga; log «retained ignorado» | Descarga; bucle de OTA en cada reconexión | bench |
| FR-OTA-05 | Imagen para esp32 (no S3); imagen truncada; imagen con la misma versión | `error:imagen`, `error:imagen`, `rechazado:misma_version` | Cambio de slot; reinicio | bench |
| FR-OTA-06 | Comando con la release B válida | `fw` = B en ≤ 120 s desde el fin de la descarga | Rollback de una imagen buena | bench |
| FR-OTA-10 | Segundo comando durante una descarga | `rechazado:ocupado`; la primera descarga termina bien | Aborto de la primera | bench |
| NFR-OTA-01 | Medidas recibidas durante una OTA de B | Intervalos en [55, 65] s | Ciclo perdido sin conexión caída | bench |

---

# Parte B — Interfaces (L1)

## 8. Driver SHT41

### 8.1 Par y protocolo

Sensor Sensirion SHT41 en I²C (C-HW-04, C-HW-05). Medida con repetibilidad
alta (comando `0xFD`, 10 ms de conversión) y sin calentador. Respuesta de
6 bytes: T (2 bytes + CRC-8) y HR (2 bytes + CRC-8; polinomio 0x31, valor
inicial 0xFF). Conversión según la hoja de datos: T = −45 + 175·S_T/65535 y
HR = −6 + 125·S_RH/65535, con la HR recortada a [0, 100].

### 8.2 Requisitos

- **FR-SEN-01** [Must] [user]: en cada ciclo, el nodo deberá obtener del SHT41
  una temperatura en °C y una humedad relativa en %, convertidas según §8.1.
- **FR-SEN-02** [Must] [derived]: una lectura con NACK, timeout de I²C o CRC
  incorrecto deberá tratarse como inválida: no se publica ninguna medida de
  ese ciclo y se incrementa `err_sensor`.
- **FR-SEN-03** [Must] [derived]: cuando el sensor vuelva a responder después
  de lecturas inválidas, el nodo deberá publicar medidas válidas en el primer
  ciclo con lectura válida, sin reiniciarse.
- **NFR-SEN-01** [Should] [derived]: tras 30 min de estabilización, la
  temperatura y la HR publicadas deberán coincidir con las de un instrumento de
  referencia situado junto al sensor dentro de **± 0,5 °C y ± 3 %HR
  (propuesto)**.

### 8.3 Contratos de verificación

```yaml
id: FR-SEN-03
verification:
  preconditions:
    - DUT en OPERATIVO publicando medidas válidas.
  stimulus:
    - Desconectar SDA del SHT41 (acción del operador o conmutador del banco)
      durante 3 ciclos; reconectar.
  expected_observations:
    - Durante la desconexión no llegan mensajes de temperatura, humedad ni punto_rocio.
    - `err_sensor` aumenta en 3 (± 1).
    - En el primer ciclo tras reconectar llegan las tres medidas válidas.
  timing: ≤ 61 s desde la reconexión
  tolerance: un ciclo
  prohibited_outcomes:
    - Publicar 0, −45, −6, NaN o el último valor válido durante la desconexión.
    - Reinicio del DUT.
    - Bloqueo del bus que requiera reinicio.
  tier: bench
  evidence: [mensajes recibidos, status antes y después, log serie]
  cleanup: [SDA conectado]
```

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-SEN-01 | Vectores crudos (S_T, S_RH) = (0, 0), (65535, 65535) y (0x6666, 0x8000) | T = −45,00 / 130,00 / 25,00 °C; HR = 0 (recortada) / 100 (recortada) / 56,50 % | HR fuera de [0, 100] | host |
| FR-SEN-02 | Trama con el CRC de T alterado; trama con el CRC de HR alterado | Lectura inválida en ambos casos | Que una mitad válida se publique sola | host |
| FR-SEN-01 | DUT con el sensor conectado, 3 ciclos | 3 lecturas válidas en el log, T ∈ [0, 50] °C | `err_sensor` > 0 | target |
| NFR-SEN-01 | Comparar 10 lecturas con la referencia tras 30 min | Diferencias medias dentro de la tolerancia | — | bench (manual, con instrumento de referencia) |

## 9. Publicador MQTT

### 9.1 Par y protocolo

Broker MQTT 3.1.1 en la LAN, TCP sin TLS, autenticación por usuario y
contraseña [user]. Keepalive de **60 s (propuesto)**. El Last Will se registra
al conectar.

### 9.2 Tópicos y payloads

| Tópico | Dirección | Payload | QoS | Retain |
|---|---|---|---|---|
| `villa/<zona>/<nodo>/temperatura` | nodo → broker | `{"v":21.4,"u":"°C","ts":1760184000}` | 0 | sí |
| `villa/<zona>/<nodo>/humedad` | nodo → broker | `{"v":48.2,"u":"%","ts":1760184000}` | 0 | sí |
| `villa/<zona>/<nodo>/punto_rocio` | nodo → broker | `{"v":10.0,"u":"°C","ts":1760184000}` | 0 | sí |
| `villa/<zona>/<nodo>/status` | nodo → broker | Diagnóstico (§9.3), o LWT `{"estado":"offline"}` | 1 | sí |
| `villa/<zona>/<nodo>/cmd/ota` | broker → nodo | `{"url":"https://…"}` (§12) | 1 | no (FR-OTA-04) |

`<zona>` sale de la configuración (§17); `<nodo>` es el identificador de §16.

### 9.3 Diagnóstico en `status` [pack:esp32]

```json
{"estado":"online","fw":"0.3.0","rssi":-61,"reset":"poweron",
 "uptime_s":3600,"lecturas":60,"err_sensor":0,"ota":"ninguno","hora_valida":true}
```

| Campo | Tipo | Valores |
|---|---|---|
| `estado` | string | `online` (publicado por el nodo) · `offline` (LWT o salida ordenada) |
| `fw` | string | Versión de la aplicación en ejecución (descriptor de la app) |
| `rssi` | entero dBm | RSSI del AP en el momento de publicar |
| `reset` | string | `poweron`, `sw`, `panic`, `task_wdt`, `int_wdt`, `brownout` u `otro` |
| `uptime_s` | entero | Segundos desde el arranque |
| `lecturas` | entero | Lecturas válidas desde el arranque |
| `err_sensor` | entero | Lecturas inválidas desde el arranque |
| `ota` | string | `ninguno`, `en_curso`, `ok`, `rechazado:<motivo>` o `error:<motivo>`: resultado de la última OTA desde el arranque |
| `hora_valida` | booleano | `true` si la hora es válida según FR-TIME-02 |

### 9.4 Requisitos

- **FR-MQTT-01** [Must] [user]: el nodo deberá publicar cada medida en
  `villa/<zona>/<nodo>/<medida>`, con `<medida>` ∈ {**`temperatura`,
  `humedad`, `punto_rocio`** (propuesto)}.
- **FR-MQTT-02** [Must] [user]: el payload de medida deberá ser un objeto JSON
  con exactamente las claves `v` (número), `u` (string: **`°C`, `%`, `°C`**
  (propuesto)) y `ts` (entero o `null`).
- **FR-MQTT-03** [Must] [user]: con hora válida (FR-TIME-02), `ts` deberá
  ser el instante de la medida en **segundos Unix UTC (propuesto)**; sin hora
  válida, `ts` deberá ser `null` (FR-TIME-03).
- **FR-MQTT-04** [Must] [derived]: los mensajes de medida deberán publicarse
  con **retain y QoS 0 (propuesto)**.
- **FR-MQTT-05** [Must] [user]: el nodo deberá registrar como Last Will
  `{"estado":"offline"}` en `status`, con retain y QoS 1, de modo que un
  suscriptor lo reciba en ≤ 100 s tras un corte de alimentación del nodo.
- **FR-MQTT-06** [Must] [user]: en cada conexión MQTT, el nodo deberá publicar
  `status` con `estado` = `online` antes que cualquier otro mensaje.
- **FR-MQTT-07** [Must] [user]: el nodo deberá autenticarse con el usuario y
  la contraseña configurados; con el usuario vacío, deberá conectarse sin
  credenciales.
- **FR-MQTT-08** [Must] [pack:esp32]: el nodo deberá publicar `status` con los
  campos de §9.3 al conectar y en cada ciclo de medición **(propuesto)**.
- **FR-MQTT-09** [Must] [pack:esp32]: el nodo deberá publicar `status` en ≤ 2 s
  tras cualquier cambio del campo `ota`.

### 9.5 Contratos de verificación

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-MQTT-01 | OPERATIVO, zona `zona1`; suscribirse a `villa/#` | Exactamente los 3 tópicos de medida bajo `villa/zona1/clima-xxxxxx/` | Tópicos con mayúsculas, espacios o `//` | bench |
| FR-MQTT-02 | Serializador con T = 21,4 y ts = 1760184000; con ts ausente | `{"v":21.4,"u":"°C","ts":1760184000}` y `…"ts":null}` | Claves adicionales; `v` como string | host |
| FR-MQTT-03 | SNTP bloqueado y luego desbloqueado (contrato de FR-TIME-03) | `ts` = null antes; tras la sincronización, \|ts − hora del broker\| ≤ 2 s | `ts` = 0, 1970 o anterior al build | bench |
| FR-MQTT-04 | Suscriptor nuevo tras una publicación | Recibe el último valor de cada medida con retain = 1 | Retain ausente | bench |
| FR-MQTT-05 | OPERATIVO; cortar la alimentación del DUT | `{"estado":"offline"}` retained en ≤ 100 s | Que el último `status` retained siga diciendo online pasado ese tiempo | bench |
| FR-MQTT-06 | Capturar los primeros mensajes tras una reconexión | El primero es `status` online | Medidas antes que `status` | bench |
| FR-MQTT-07 | Broker con autenticación; DUT con credenciales erróneas, y después correctas | Con las erróneas: CONECTANDO_BROKER con backoff; con las correctas: OPERATIVO | Reinicio; bucle de conexión sin backoff | bench |
| FR-MQTT-08 | 3 ciclos tras conectar | Un `status` al conectar y uno por ciclo, todos con los 9 campos y sus tipos | Campos ausentes o con otro tipo | bench |
| FR-MQTT-09 | Publicar un comando OTA con `http://` | `status` con `ota` = `rechazado:host` en ≤ 2 s | Esperar al ciclo siguiente | bench |

## 10. Discovery de Home Assistant

### 10.1 Par

Integración MQTT de Home Assistant, con el prefijo `homeassistant` (assumed).

### 10.2 Esquema (una configuración por medida)

Tópico `homeassistant/sensor/<nodo>/<medida>/config`, retain, QoS 1:

```json
{"name":"Temperatura","unique_id":"clima-a1b2c3_temperatura",
 "state_topic":"villa/zona1/clima-a1b2c3/temperatura",
 "value_template":"{{ value_json.v }}","unit_of_measurement":"°C",
 "device_class":"temperature","state_class":"measurement","expire_after":180,
 "availability_topic":"villa/zona1/clima-a1b2c3/status",
 "availability_template":"{{ value_json.estado }}",
 "payload_available":"online","payload_not_available":"offline",
 "device":{"identifiers":["clima-a1b2c3"],"name":"Clima zona1",
           "model":"ESP32-S3-DevKitC-1 + SHT41","sw_version":"0.3.0"}}
```

`humedad`: `device_class` = `humidity`, unidad `%`. `punto_rocio`:
`device_class` = `temperature`, unidad `°C`, nombre «Punto de rocío».

### 10.3 Requisitos

- **FR-HA-01** [Must] [user]: en cada conexión MQTT, el nodo deberá publicar
  con retain las tres configuraciones de Discovery, después de `status` y antes
  de la primera medida.
- **FR-HA-02** [Must] [derived]: cada configuración deberá contener los campos
  de §10.2, con `unique_id` = `<nodo>_<medida>` y `sw_version` = la versión en
  ejecución.
- **FR-HA-03** [Should] [derived]: cada configuración deberá declarar
  `expire_after` = **180 s (propuesto)**.

### 10.4 Contratos de verificación

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-HA-01 | Broker limpio; conectar el DUT | 3 tópicos `…/config` retained, en orden status → config → medidas | Configuraciones tras las medidas | bench |
| FR-HA-02 | Generador de configuración con nodo `clima-a1b2c3`, zona `zona1` y fw `0.3.0` | JSON idéntico campo a campo a §10.2 | `unique_id` dependiente de la zona | host |
| FR-HA-01/02 | Home Assistant real con la integración MQTT | Aparece 1 dispositivo con 3 entidades y valores en °C/% | Entidades duplicadas tras reconectar | bench |
| FR-HA-03 | DUT en OPERATIVO; desconectar SDA del SHT41 > 180 s (`status` sigue online) | HA marca las 3 entidades como no disponibles en ≤ 190 s | Valor obsoleto mostrado como actual | bench |

## 11. Portal cautivo

### 11.1 Par

Teléfono u ordenador del instalador, unido al AP abierto del nodo. Servidor
HTTP en `192.168.4.1`, puerto 80; el DNS responde con `192.168.4.1` a toda
consulta A.

### 11.2 Requisitos

- **FR-POR-01** [Must] [user]: en PORTAL, el nodo deberá emitir un AP Wi-Fi
  abierto con SSID = el identificador del nodo (§16).
- **FR-POR-02** [Must] [derived]: el portal deberá responder a
  `GET /generate_204` y `GET /hotspot-detect.html` con una redirección 302 a
  `http://192.168.4.1/`, y el DNS deberá resolver cualquier nombre a
  `192.168.4.1`.
- **FR-POR-03** [Must] [user]: `GET /` deberá servir un formulario con los
  siete campos de §17 que se configuran por el portal.
- **FR-POR-04** [Must] [derived]: un envío con algún campo fuera de las reglas
  de validación de §17 **(propuesto)** deberá responderse con el error del
  campo y no deberá modificar la NVS.
- **FR-POR-05** [Must] [derived]: un envío válido cuya unión STA no obtenga IP
  en ≤ **20 s (propuesto)** deberá responderse con «no se pudo conectar»,
  dejando el AP activo y la NVS sin cambios.
- **FR-POR-06** [Must] [derived]: un envío válido con unión STA exitosa deberá
  persistir la configuración y reiniciar el nodo en ≤ **5 s (propuesto)**;
  tras el reinicio, el nodo arranca por T01.
- **FR-POR-07** [Must] [derived]: fuera de PORTAL y VALIDANDO, el nodo no
  deberá emitir ningún AP ni servir HTTP.

### 11.3 Contratos de verificación

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-POR-01 | NVS borrada; arrancar | SSID `clima-xxxxxx` abierto en el escaneo en ≤ 10 s | AP con contraseña; SSID con la zona | bench |
| FR-POR-02 | Unido al AP: `GET /generate_204`; consulta DNS de `example.com` | 302 a `http://192.168.4.1/`; A = 192.168.4.1 | 204 (el teléfono no mostraría el portal) | bench |
| FR-POR-03 | `GET /` | HTML con los 7 campos nombrados en §17 | Campos rellenos con secretos | bench |
| FR-POR-04 | Validador con cada caso límite de §17 (longitud 0, máximo y máximo + 1; `zona` con `/`, `+`, `#`, mayúsculas o espacio) | Rechazo con el campo nombrado | Aceptar un valor inválido; escribir en la NVS (lectura de NVS en target) | host + target |
| FR-POR-05 | Envío con una contraseña Wi-Fi errónea | «no se pudo conectar» en ≤ 25 s; el AP sigue visible; la NVS no cambia | Persistir; reiniciar | bench |
| FR-POR-06 | Envío con datos correctos | El AP desaparece en ≤ 5 s; el log serie muestra el reinicio, T01 con la zona enviada y `wifi_up` | Volver a PORTAL tras reiniciar | bench |
| FR-POR-07 | DUT configurado (CONECTANDO_WIFI o posterior); escaneo y `GET http://<ip-dut>/` | Ningún SSID `clima-*`; conexión rechazada | Respuesta HTTP | bench |

## 12. Receptor de comandos OTA

### 12.1 Esquema

Tópico `villa/<zona>/<nodo>/cmd/ota`. Payload `{"url":"<string, 1–512 bytes>"}`.
Un payload que no sea JSON, que no tenga `url` o que tenga claves extra se
rechaza con `rechazado:payload`.

### 12.2 Requisitos

- **FR-OTA-01** [Must] [user]: en OPERATIVO, el nodo deberá aceptar comandos
  OTA en `villa/<zona>/<nodo>/cmd/ota` con el esquema de §12.1 y entregarlos a
  la política de §7.
- **FR-OTA-09** [Must] [derived]: un payload que no cumpla §12.1 deberá
  rechazarse con `rechazado:payload` sin descargar nada.

### 12.3 Contratos de verificación

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-OTA-01 | Publicar `{"url":"https://github.com/…/clima.bin"}` válido | `status` con `ota` = `en_curso` en ≤ 2 s | Ignorar el comando | bench |
| FR-OTA-09 | Parser con `{}`, `{"url":5}`, `no-json`, URL de 513 bytes y `{"url":"…","x":1}` | `rechazado:payload` en todos | Fallo de memoria; aceptación | host |

---

# Parte C — Fundación (L0)

## 13. Wi-Fi, DNS y sincronización de hora (SNTP)

ESP-IDF `esp_wifi` (STA, y AP+STA solo en PORTAL y VALIDANDO), `esp_netif`,
DHCP y el cliente SNTP de lwIP. Se configuran y se usan; no se implementan, y
se prueban de forma transitiva a través de §6, §9 y §11. Orden de arranque: la
NVS, después la pila Wi-Fi y, tras T08, SNTP.

La **regla de validez de la hora** sí es código propio: una función pura
(sincronizado en este arranque, reloj actual, fecha de build → válida o no) que
se prueba en host.

### 13.1 Requisitos de hora

- **FR-TIME-01** [Must] [user]: tras cada `wifi_up` (T08), el nodo deberá
  sincronizar el reloj por SNTP con **`pool.ntp.org` (propuesto)** y, si el
  servidor es alcanzable, tener hora válida en ≤ **30 s (propuesto)**.
- **FR-TIME-02** [Must] [user]: la hora deberá considerarse válida solo si se
  completó una sincronización SNTP desde el último arranque **y** el reloj
  resultante no es anterior a la fecha de build del firmware. En cualquier
  otro caso, la hora no es válida.
- **FR-TIME-03** [Must] [user]: sin hora válida, el nodo deberá publicar cada
  medida con `"ts": null` y `status` con `hora_valida` = `false`; ningún
  mensaje deberá llevar un `ts` anterior a la fecha de build (en particular,
  ninguna fecha de 1970).
- **FR-TIME-04** [Should] [derived]: el nodo deberá resincronizar cada **1 h
  (propuesto)**; una resincronización fallida no deberá invalidar una hora ya
  válida.
- **FR-TIME-05** [Must] [user]: la falta de hora válida no deberá retrasar ni
  impedir la medición ni la publicación.

### 13.2 Contratos de verificación

```yaml
id: FR-TIME-03
verification:
  preconditions:
    - DUT configurado; el banco bloquea UDP/123 (SNTP) hacia fuera; broker accesible.
  stimulus:
    - Cortar y devolver la alimentación del DUT; mantener SNTP bloqueado 5 min; desbloquearlo.
  expected_observations:
    - Mientras SNTP está bloqueado, todas las medidas llegan con "ts": null y `status` con hora_valida = false.
    - Tras desbloquear, en ≤ 30 s, las medidas llevan ts entero con |ts − hora del broker| ≤ 2 s, y hora_valida = true.
  timing: ≤ 30 s desde el desbloqueo hasta el primer ts válido (más hasta 60 s de ciclo)
  tolerance: un ciclo de medición
  prohibited_outcomes:
    - Cualquier ts < fecha de build del firmware (incluidos 0 y 1970).
    - Que falte una publicación por no tener hora (viola FR-TIME-05).
    - Que la clave ts desaparezca del JSON (viola FR-MQTT-02).
  tier: bench
  evidence: [todos los mensajes de medida y status de la ventana, instantes de bloqueo y desbloqueo]
  cleanup: [SNTP desbloqueado]
```

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-TIME-01 | SNTP accesible; `wifi_up` | `hora_valida` = true en ≤ 30 s (log y `status`) | Nunca sincronizar | bench |
| FR-TIME-02 | Función de validez: (sincronizado = no, reloj = 2030), (sí, reloj = 1970), (sí, reloj = build − 1 s), (sí, reloj = build + 1 s) | No válida, no válida, no válida, válida | Considerar válido un reloj solo porque «parece reciente» | host |
| FR-TIME-02 | Reinicio por software (`esp_restart`) tras una sincronización, con SNTP bloqueado | `hora_valida` = false tras el reinicio | Reutilizar sin resincronizar la hora del RTC del arranque anterior | target |
| FR-TIME-04 | Hora válida; bloquear SNTP 2 h | `hora_valida` sigue en true; el log registra el intento fallido de resincronización | Pasar a `ts` = null | bench |
| FR-TIME-05 | SNTP bloqueado desde el arranque | Primera medida en ≤ 30 s (FR-CON-05) con `ts` = null | Esperar a la hora para publicar | bench |

## 14. Cliente MQTT y HTTPS OTA

`esp-mqtt` (componente gestionado en ESP-IDF 6.x) y `esp_https_ota` con el
bundle de certificados de ESP-IDF. El rollback lo ejecuta el bootloader con la
validación de la aplicación habilitada. Se prueban de forma transitiva a
través de §7, §9 y §12.

## 15. NVS, I²C, FreeRTOS y watchdog

- NVS en la partición `nvs` (§2.2); la configuración se escribe de forma
  atómica (todo o nada) en T05.
- Driver I²C maestro de ESP-IDF (C-HW-04, C-HW-05).
- **NFR-WDT-01** [Must] [pack:esp32]: si la tarea de medición o la de
  conectividad dejan de alimentar el watchdog de tareas durante **30 s
  (propuesto)**, el nodo deberá reiniciarse, y su siguiente `status` deberá
  mostrar `reset` = `task_wdt`.

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| NFR-WDT-01 | Build de prueba con un comando serie que bloquea la tarea de medición | Reinicio en 30 s (+ 2 s); `status` posterior con `reset` = `task_wdt` | Que el nodo quede colgado; que el build de producción incluya el comando | target |
| NFR-WDT-01 | Funcionamiento de 24 h con cortes de broker | 0 reinicios por watchdog | Reinicios espurios del watchdog | bench |

---

# Parte D — Aspectos transversales

## 16. Identidad del nodo

- **FR-ID-01** [Must] [derived]: el identificador del nodo deberá ser
  **`clima-` seguido de los 3 últimos bytes de la MAC STA en hexadecimal en
  minúsculas (propuesto)** (p. ej., `clima-a1b2c3`), y deberá ser estable entre
  reinicios y OTA.

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-ID-01 | Función con la MAC `24:0A:C4:A1:B2:C3` | `clima-a1b2c3` | Mayúsculas; otro prefijo | host |
| FR-ID-01 | Comparar el id del log serie (y el SSID del portal) a lo largo de 3 reinicios | Idéntico | Cambio del id | bench |

## 17. Catálogo de configuración

| Nombre | Tipo | Por defecto | Validación (propuesto, D11) | Persistencia | Sensibilidad | Interfaz | Efecto | Reset |
|---|---|---|---|---|---|---|---|---|
| `wifi_ssid` | string | ninguno | 1–32 bytes | NVS | operativa (identifica la red) | portal | reinicio (T05) | se borra con la NVS |
| `wifi_pass` | string | vacío | vacío (red abierta) u 8–63 ASCII imprimible | NVS | **secreto** | portal | reinicio | se borra con la NVS |
| `mqtt_host` | string | ninguno | 1–63 caracteres `[A-Za-z0-9.-]`, nombre de host o IPv4 decimal | NVS | operativa | portal | reinicio | se borra con la NVS |
| `mqtt_port` | entero | 1883 | 1–65535 | NVS | pública | portal | reinicio | se borra con la NVS |
| `mqtt_user` | string | vacío | 0–64 bytes | NVS | operativa | portal | reinicio | se borra con la NVS |
| `mqtt_pass` | string | vacío | 0–64 bytes | NVS | **secreto** | portal | reinicio | se borra con la NVS |
| `zona` | string | ninguno | `^[a-z0-9_-]{1,32}$` | NVS | operativa (puede identificar la vivienda) | portal | reinicio | se borra con la NVS |
| Hosts OTA permitidos | lista | §7 | — | firmware | pública | build | nueva imagen | — |
| Servidor SNTP | string | `pool.ntp.org` | — | firmware | pública | build | nueva imagen | — |
| `{{ota_repo}}` | string | `<owner>/villa-nodo-clima-piloto` | `owner/repo` de GitHub | firmware | pública | build | nueva imagen | — |

- **FR-CFG-01** [Must] [user]: la configuración aprobada en el portal deberá
  mantenerse tras cortes de alimentación y OTA, hasta que se borre la NVS.
- **C-CFG-01** [Must] [user]: ningún campo de configuración en tiempo de
  ejecución debe tener un valor por defecto compilado que identifique una red,
  un broker o una ubicación.

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| FR-CFG-01 | Nodo configurado; 5 cortes de alimentación | El log serie muestra cada vez T01 con la misma zona | Abrir el portal | bench |
| FR-CFG-01 | Nodo configurado; OTA A → B (Fase 3) | B publica en los mismos tópicos `villa/<zona>/…` | Abrir el portal | bench |
| C-CFG-01 | Revisar `sdkconfig.defaults`, Kconfig y el código fuente | Sin valores por defecto para los 5 campos de cadena | — | other (revisión + CI) |

## 18. Observabilidad

El log serie (USB-Serial/JTAG) registra cada transición de §6.3 como
`con: <ESTADO> -> <ESTADO> (<evento>)`, cada ciclo de medición y cada decisión
OTA. Los tests consumen ese formato de log; cambiarlo es un cambio de
interfaz. El diagnóstico remoto es `status` (§9.3).

## 19. Seguridad

### 19.1 Perfil de amenazas — «LAN doméstica, repositorio público»

| Elemento | Supuesto |
|---|---|
| Actores | (a) Cualquiera en Internet que lea el repositorio público y las releases; (b) un dispositivo o persona dentro de la LAN; (c) alguien al alcance de radio durante el aprovisionamiento; (d) alguien con acceso físico al nodo |
| Red de confianza | Ninguna para la confidencialidad; la LAN se considera observable |
| Exposición remota | Ningún puerto de escucha en OPERATIVO (FR-POR-07); solo conexiones salientes (MQTT, SNTP, HTTPS) |
| Confidencialidad | Las credenciales no deben salir del nodo por ninguna interfaz que este controle. **No se reclama confidencialidad en reposo** ni en el tránsito MQTT |
| Integridad / autenticidad del firmware | Origen autenticado por TLS frente a una lista de hosts permitidos; sin firma de imagen |
| Ciclo de vida de credenciales | Se introducen por el portal y solo se borran con la NVS; nunca se muestran de vuelta |
| Secure Boot / cifrado de flash | Deshabilitados (riesgos aceptados en §4) |
| Recuperación | Borrar la NVS por USB devuelve el nodo a PORTAL |

**Riesgos aceptados.** (b) puede leer las credenciales MQTT y falsear medidas
o comandos, pero no puede instalar un firmware fuera de los hosts permitidos.
(c) puede leer las credenciales Wi-Fi enviadas al AP abierto durante el
aprovisionamiento. (d) puede extraer las credenciales leyendo la flash. Una
cuenta de GitHub comprometida puede distribuir firmware.

### 19.2 Requisitos

- **NFR-SEC-01** [Must] [user]: el repositorio no deberá contener
  credenciales, SSIDs, direcciones de broker o IP de la instalación, nombres de
  zona reales ni datos que identifiquen el lugar de instalación, en ningún
  fichero ni en el historial de git.
- **NFR-SEC-02** [Must] [derived]: las imágenes de firmware publicadas no
  deberán contener SSIDs, contraseñas, hosts de broker ni zonas.
- **FR-SEC-03** [Must] [derived]: el nodo no deberá emitir `wifi_pass` ni
  `mqtt_pass` por el log serie, por MQTT ni por HTTP.
- Las reglas OTA de seguridad son FR-OTA-02, FR-OTA-03 y FR-OTA-04 (§7).

| ID | Precondición · estímulo | Observación esperada | No debe ocurrir | Nivel |
|---|---|---|---|---|
| NFR-SEC-01 | Escáner de secretos (p. ej., gitleaks) sobre el árbol y el historial, más una lista de patrones prohibidos guardada fuera del repo, en cada push | 0 hallazgos | Que la CI pase con hallazgos | other (CI) |
| NFR-SEC-02 | Release binaria + `strings`, buscando los valores del banco (que residen fuera del repo) | 0 coincidencias | Cualquier coincidencia | other (CI) / bench |
| FR-SEC-03 | Aprovisionar con contraseñas marcador únicas; capturar el log serie del arranque, del portal y de 3 ciclos, y suscribirse a `#` | El marcador no aparece en ninguna captura | Que aparezca, aunque sea parcial o en base64 | bench |

## 20. Build

Las restricciones C-HW-* y C-BLD-* (§2.2) y C-CFG-01 (§17) son las que lee el
build. Los componentes gestionados, el `sdkconfig` y la versión exacta de
ESP-IDF son HOW y están en `docs/Method/project/arquitectura.md`.

---

# Parte E — Operación y verificación

## 21. Procedimientos operativos (ruta de lectura)

Flashear por USB (C-BLD-*) → aprovisionar por el portal (§11) → operar: las
medidas llegan a HA (§5, §9, §10) → actualizar por OTA (§7, §12) →
recuperarse: automático ante cortes (§6), rollback (FR-OTA-07); manual,
borrando la NVS para reaprovisionar (§19.1). Los pasos concretos están en
`docs/UserDocumentation/Manual-de-usuario.md`.

## 22. Verificación y validación

### 22.0 Arquitectura de pruebas

| Nivel | Dónde | Qué cubre aquí |
|---|---|---|
| host | PC, compilador nativo, sin ESP-IDF | Validez de la hora, punto de rocío, redondeo, conversión y CRC del SHT41, serialización JSON, generador de Discovery, validación de §17, política OTA, parser de comandos, backoff, lógica de la tabla de transiciones, identificador |
| target | ESP32-S3 real | Lectura I²C, NVS, servidor HTTP del portal, watchdog |
| bench | DUT + AP Wi-Fi + broker + HA + operador | Recuperación, LWT, OTA y rollback, portal de extremo a extremo, ausencia de reinicios, exactitud |
| other | CI / revisión | Secretos en el repo y en las releases, C-CFG-01 |

Correspondencia con capas: L2 en host como funciones puras; L1 con su núcleo
puro en host y el cable/flujo en target o bench; L0 de forma transitiva, sin
tests propios. La matriz componente × nivel se genera desde
`testing/test-plan.yaml` (`/build`), no se mantiene a mano.

### 22.1 Pruebas de aceptación

1. **Instalación en limpio.** NVS borrada → portal → aprovisionamiento → las
   entidades aparecen en HA en ≤ 2 min.
2. **24 h de estabilidad.** 1440 ± 2 publicaciones por medida, 0 reinicios,
   con 3 cortes de broker y 2 de Wi-Fi intercalados.
3. **Ciclo OTA completo.** A → B por comando; luego B → C, con C provocando el
   rollback a B.

### 22.2 Trazabilidad

Es generada: la produce el informe de `/build` a partir de los IDs de este
documento y de las entradas de `testing/test-plan.yaml`. No hay columna de
cobertura en este FSD.

---

## Apéndice A — Constantes

| Constante | Valor | Requisito |
|---|---|---|
| Periodo de medición | 60 s | FR-MED-01 |
| Backoff inicial / techo | 1 s / 60 s | FR-CON-02 |
| Keepalive MQTT | 60 s | FR-MQTT-05 |
| Prueba de unión del portal | 20 s | FR-POR-05 |
| Ventana de validación de imagen | 300 s | FR-OTA-07 |
| Timeout del watchdog | 30 s | NFR-WDT-01 |
| `expire_after` | 180 s | FR-HA-03 |
| Magnus b / c | 17,62 / 243,12 °C | FR-MED-03 |
| Dirección del SHT41 / comando | 0x44 / 0xFD | §8.1 |
| IP del portal | 192.168.4.1 | §11 |
| Servidor SNTP / plazo / resincronización | `pool.ntp.org` / 30 s / 1 h | FR-TIME-01, FR-TIME-04 |
| Hosts OTA / redirecciones máx. | `github.com`, `release-assets.githubusercontent.com` / 3 | FR-OTA-02 |

## Relacionado

- `docs/00-Overview.md` — mapa de planos.
- `docs/Method/AI-Workflow.md` — contrato de build.
- `docs/UserDocumentation/Manual-de-usuario.md` — manual.
