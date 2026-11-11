# Verificación de las correcciones de la auditoría de seguridad de la Fase 2

- **Fecha:** 2026-11-10
- **Auditoría de origen:** `testing/auditoria-seguridad-fase-2.md` (sobre `d4236cc`)
- **Commit verificado:** `d2c67df` (HEAD de `main`), diff `d4236cc..HEAD` (11 commits)
- **Método:** solo lectura del código, de los workflows, del FSD 0.9.8 y de las evidencias de
  `test-results/`. No se compiló, no se grabó, no se ejecutó ningún test ni se llamó al banco
  ni a ninguna IP. No hay fuentes de ESP-IDF/lwIP en esta máquina, así que el comportamiento
  interno de lwIP y de `esp_http_server` que cito sale de cómo conozco esas pilas, no de leer
  su código: lo marco como **por verificar** donde importa.

## Resumen

- Las seis correcciones con código (SEC-04 a SEC-09) existen, se corresponden con lo que pedía
  la auditoría y no tienen errores de memoria, de concurrencia bajo `s_lock` ni de regresión
  visibles en el portal o la conectividad. Las regresiones de banco registradas lo confirman
  (p. ej., TC-POR-12: T24 a 600 000 ms exactos de T02).
- **SEC-05 queda parcial.** El contador de esperas vuelve a 0 con cada byte recibido. Un cliente
  lento que envíe 1 byte cada ~14 s sigue reteniendo la única tarea del servidor (hasta unas
  4 h con un cuerpo de 1024 B), y `lru_purge_enable` no lo evita.
- **SEC-06 queda parcial (por verificar).** La protección filtra por la IP de destino, no por la
  interfaz de entrada. Con el modelo de host débil de lwIP, un equipo de la LAN que envíe
  paquetes a 192.168.4.1 hacia la MAC del STA del nodo pasaría los dos filtros durante
  VALIDANDO.
- Hay dos efectos secundarios menores de SEC-04: `portal_dns_detener` probablemente no termina la
  tarea DNS, y `httpd_stop` puede bloquear la tarea `esp_timer`.
- En el diff no hay **nada no relacionado ni sospechoso**: no hay sockets nuevos fuera del DNS ya
  existente, ni IPs nuevas aparte de 192.168.4.1, ni descargas o secretos nuevos. Todos los
  ficheros tocados pertenecen a alguno de los hallazgos o a sus evidencias.

## Tabla de verificación

| ID | Veredicto | Archivo:línea | Explicación | Qué falta |
|---|---|---|---|---|
| SEC-04 | **Corregido** (con dos observaciones menores) | `main/main.c:570-591`, `:672-675`, `:545`, `:567`; `components/conectividad/conectividad.c:23-26`; `components/portal/portal_dns.c`, `portal_http.c:206-210` | El temporizador de 10 min arranca en T02. T24 pasa a ESPERA, y en ESPERA ninguna fila acepta «envío», así que en el segundo que tarda en cerrarse un POST recibe «errores» y no toca la NVS. El cierre corre en otro disparo del temporizador, sin `s_lock`, lo que evita el interbloqueo con `al_enviar`. T25 aplaza el cierre y lo reemite tras T06 o tras un fallo de NVS. La prueba de host TC-CON-01 cubre T24, T25 y que ESPERA no tenga filas. La de banco TC-POR-12 discrimina bien: control positivo del AP antes, ±5 s, AP ausente después, medición sin NVS ni reinicio, y reabierto tras un reset. Lo que se pedía era limitar la ventana. La toma de control *dentro* de los 10 min sigue siendo posible y queda aceptada en §19.1 (c). | (a) **Prolongación por el propio atacante:** tras cada T06 hay 1 s en PORTAL antes de reemitir `portal_vence`. Un cliente que envíe otro formulario en ese segundo vuelve a VALIDANDO, y el temporizador da otra vez T25. Repitiéndolo cada ~20 s, el AP sigue abierto indefinidamente. Solo lo aprovecha quien ya estaba dentro de la ventana, así que el impacto es bajo, pero contradice «como máximo 10 min». Se arregla emitiendo T24 directamente en `no_conecta` cuando `s_cierre_pendiente`, o rechazando envíos con el cierre pendiente. (b) Ver «efectos secundarios» más abajo. |
| SEC-05 | **Parcial** | `components/portal/portal_lectura.c:5-9`; `portal_http.c:107-123`, `:190` | Resuelve el caso exacto de la auditoría: `Content-Length` y ningún byte dan 408 a las 3 esperas (~15 s con `recv_wait_timeout` = 5 s). TC-POR-13 prueba de verdad esa función pura, incluido «nunca sin límite» si no llega nada. **Se puede saltar:** el contador cuenta esperas *seguidas* y vuelve a 0 con cada dato, así que basta mandar 1 byte antes de la tercera espera. Con `BODY_MAX` = 1024, una sola conexión retiene la única tarea de `esp_http_server` hasta ~1024 × 14 s ≈ 4 h. Durante ese tiempo no se aceptan conexiones nuevas, porque `accept` y los manejadores corren en la misma tarea, y `lru_purge_enable` no actúa. Es un DoS del aprovisionamiento desde el AP abierto, y combinado con T24 consume la ventana de 10 min del propietario. Se ajusta a FR-POR-09 y D25 tal como están escritos, pero no al escenario de la auditoría («retener la tarea»). | Añadir un plazo total para el cuerpo (p. ej., ≤ 15-20 s desde el inicio del POST, con `esp_timer_get_time`) o un mínimo de bytes por espera, y una prueba de host con «1 byte por espera». Si se acepta tal cual, registrarlo en §19.3. |
| SEC-06 | **Parcial** (bypass por verificar) | `components/portal/portal_dns.c:19-27`; `portal_http.c:160-181`; `portal_origen.c:8-10` | El DNS ya no se liga a `INADDR_ANY` sino a 192.168.4.1. El HTTP cierra en `open_fn` toda conexión cuya dirección local no sea 192.168.4.1, y lo hace de forma segura ante fallos: si `getsockname` falla o la conexión es IPv6 nativa, la IP queda a 0 y se rechaza. También maneja bien la IPv4 mapeada `::ffff:` del socket dual de `esp_http_server` (con `CONFIG_LWIP_IPV6=y`). Esto cierra el escenario de la auditoría: un equipo de la LAN que ataca a la IP del STA. **Bypass por verificar:** lwIP acepta, por defecto, un paquete dirigido a cualquier IP propia aunque entre por otra interfaz (host débil, `ip4_input` recorre todas las `netif`). Un equipo de la misma LAN puede añadir la ruta «192.168.4.1 vía la IP del STA del nodo». Entonces los paquetes llegan por el STA con destino 192.168.4.1, el DNS ligado los acepta y el HTTP ve la dirección local 192.168.4.1. Solo funciona en VALIDANDO (≤ 20 s) y el impacto sigue siendo bajo (T07 rechaza el segundo envío). TC-POR-14 prueba la función pura, no ese camino. FR-POR-10 dice literalmente «lo que llega dirigido a la IP del AP», así que el bypass cumple la letra del requisito pero no su intención. | Confirmarlo en banco o leyendo `ip4_input` de la lwIP de ESP-IDF 6.0.2. Si se confirma: filtrar por interfaz (`SO_BINDTODEVICE` en el DNS si la lwIP de ESP-IDF lo admite; en el HTTP, comparar la IP del cliente con la subred 192.168.4.0/24) o aceptarlo en §19.3. |
| SEC-07 | **Corregido** | `main/main.c:265-276`; `components/conectividad/conectividad_sta.c:5-12` | Con clave, `threshold.authmode = WIFI_AUTH_WPA2_PSK` (umbral mínimo: admite WPA2/WPA3, rechaza abierta, WEP y WPA). `pmf_cfg.capable = true` y `required = false`. Sin clave, abierta. Se aplica tanto en CONECTANDO_WIFI (`arrancar_sta`) como en la prueba de unión (`probar_union`), como pide FR-CON-07. TC-CON-13 prueba la función pura. TC-CON-14 (gemelo abierto 180 s, con control positivo de ≥ 3 intentos y comprobación de la lista de estaciones) es una buena prueba, pero **no discrimina el arreglo**: también pasó sin él (`test-results/20261110T224654Z-316a70b/`), porque ESP-IDF 6.0.2 ya subía el umbral. La traducción del núcleo a `wifi_config_t` (main.c:272) no tiene prueba propia; queda cubierta por revisión. | Nada bloqueante. Efecto colateral aceptado: un router solo WPA1/TKIP deja de funcionar. |
| SEC-08 | **Corregido** (correspondencia SHA ↔ versión por verificar) | `.github/workflows/*.yml` (todas las `uses:`); `.devcontainer/Dockerfile:4,18`; `build.yml:32`, `:170-180`; `ci.yml:32`; `scripts/ci/requirements.txt`; `tests/bench/requirements.txt` | No queda ninguna `uses:` por etiqueta. Todas van por SHA de 40 caracteres con la versión en un comentario. La imagen `espressif/idf` va por digest en la CI y en el Dockerfile. pip usa `--require-hashes` en la CI y en el Dockerfile, con las dependencias transitivas del nivel bench declaradas: 10 paquetes y 190 hashes. Si faltara una, pip fallaría y la CI estaría en rojo. `softprops/action-gh-release` se ha sustituido por `gh release create --verify-tag`, con el tag pasado por `env:`. El token `contents: write` solo lo tiene el job `release`, que ya no ejecuta código de terceros. | Sin red no puedo comprobar que cada SHA sea de verdad el commit de la versión del comentario (v4.4.0, v4.6.2, v4.3.0), ni que el digest sea el de `v6.0.2`: **por verificar**. La release con `gh` no se ha ejecutado nunca (primer tag, §19.3). `gh` del Dockerfile se instala por `apt` sin fijar versión, igual que antes; es un riesgo menor fuera del alcance. |
| SEC-09 | **Corregido** | `.github/workflows/build.yml:55-81` | Los inputs llegan por `env:` y ya no se interpolan en el script. La variante se comprueba contra una lista cerrada (`case`). La versión, venga del input, del tag o de `0.0.0-<sha>`, se valida con una regex semver anclada (`^…$`, sin metacaracteres de shell posibles) antes de usarse. Revisé las demás interpolaciones en `run:`: `steps.plan.outputs.variant` (`:120`), ya validada; `github.ref_name`, por `env:`. La evidencia del control (run con `0.1.0"; echo INYECTADO; "` rechazado) está en `testing/puerta-s1.md`; no la he podido comprobar en GitHub. | Nada. |
| SEC-10 | **Correcto como requisito de Fase 3** | FSD 0.9.8 `:259-262` (C-BLD-04), `:277`, §3.4 criterios de salida `:396-397`; `sdkconfig:699` | C-BLD-04 exige `CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y`, con verificación en la CI sobre el `sdkconfig` generado, y es criterio de salida de la Fase 3. Hoy sigue «is not set», como corresponde (no implementado en S1, §3.5). El anti-rollback por eFuse no se adopta, y está registrado en §19.3. | Implementarlo al empezar la Fase 3; exige grabar por USB. |
| SEC-11 | **Correcto como requisito de Fase 3** | FSD `:794-815` (FR-OTA-03, -05, -13, -14), `:907-918` (contratos) | Cubre todo lo que pedía la auditoría: anti-downgrade para `v*` (`rechazado:version_anterior`); `ota-test-*` rechazadas en producción (`rechazado:ruta`) con comprobación también en la CI; URL estricta (esquema, host completo, sin `userinfo`, puerto 443, sin `%`, `.`, `..`, `\` ni controles) con casos de prueba concretos, incluido `github.com.evil.example`; nombre del certificado obligatorio. La firma de imagen no se adopta: «una cuenta de GitHub comprometida puede distribuir firmware» queda aceptado en §19.1. | Implementación y pruebas en la Fase 3. |
| SEC-02, SEC-03, SEC-12, SEC-13, SEC-14, SEC-15 | **Documentados** | FSD §19.3 `:1452-1466`, §19.1 | Cada uno tiene su fila en §19.3 con decisión y revisión antes de cada release. Las medidas recomendadas en la auditoría están recogidas (ACL MQTT mínima, `mqtt_host` por IP, revisión de avisos de Espressif y del changelog de esp-mqtt). SEC-01 también figura, con la mitigación verificada por el propietario (no comprobable por mí). | Nada para S1. |

## Efectos secundarios encontrados (nuevos, severidad baja)

| ID | Veredicto | Archivo:línea | Explicación | Recomendación |
|---|---|---|---|---|
| N-01 | **Nuevo problema** (bajo, por verificar) | `components/portal/portal_dns.c:51-56` | `portal_dns_detener` hace `shutdown()` sobre un socket **UDP**. En lwIP, `lwip_shutdown` solo funciona con TCP y, si no recuerdo mal, devuelve `EOPNOTSUPP` sin despertar al `recvfrom` bloqueado (el socket no tiene `SO_RCVTIMEO`). La tarea DNS se quedaría bloqueada para siempre y el socket seguiría ligado a 192.168.4.1:53. Con el AP apagado no llega nada, así que no es explotable, pero el requisito «detener el DNS» de FR-POR-08 no se cumpliría de verdad y TC-POR-12 no lo comprueba: solo mira que el AP ya no se vea. | Poner `SO_RCVTIMEO` (p. ej., 1 s) en el socket para que el bucle vea `s_detener`, o cerrar el socket con `close()`. Añadir a TC-POR-12 una línea de log de «dns detenido» y comprobarla. |
| N-02 | **Nuevo problema** (bajo) | `main/main.c:580-585`; `components/portal/portal_http.c:206-210` | `al_cerrar_portal` llama a `httpd_stop` desde la tarea `esp_timer`. `httpd_stop` espera a que la tarea del servidor termine, y esa tarea no atiende la orden de parada hasta acabar el manejador en curso. Con un POST lento (SEC-05, hasta ~4 h) o simplemente uno en curso (≤ 15 s), la tarea `esp_timer` se queda bloqueada todo ese tiempo, junto con todos los temporizadores del sistema, y el AP sigue encendido hasta que acaba (`esp_wifi_stop` va después). No permite tomar el control, porque el estado ya es ESPERA. | Se resuelve casi entero con el plazo total de SEC-05. Además, se puede llamar a `esp_wifi_stop` *antes* de `httpd_stop`, o hacer la parada en una tarea propia en lugar de en `esp_timer`. |
| N-03 | Observación | `components/portal/portal_dns.c:27-34` | Si `bind` a 192.168.4.1 falla 20 veces (10 s), la tarea registra `dns: no se pudo abrir UDP/53` y termina, pero `portal_dns_iniciar` ya devolvió `ESP_OK`: el portal sigue sin DNS cautivo. No es un problema de seguridad: falla cerrado. La regresión de d64e5a3 no mostró ese error. | Ninguna para S1. Si se quiere, que T02 compruebe el resultado. |
| N-04 | Cosmético | `components/portal/portal_http.c:190-191` | Hay dos comentarios en la línea de `cfg.open_fn`, y el de SEC-05 (`lru_purge_enable`) está desplazado a la línea equivocada. | Moverlo. |

## Revisión del diff completo `d4236cc..HEAD` (puerta trasera)

- **Ficheros tocados:** solo `components/portal`, `components/conectividad`, `main/main.c`,
  `.github/workflows`, `.devcontainer/Dockerfile`, `scripts/ci/requirements.txt`,
  `tests/host`, `tests/bench` (`test_seguridad.py`, `requirements.txt`), FSD, `testing/` y
  `test-results/`. Ninguno queda fuera de los hallazgos.
- **Código nuevo de firmware:** no hay sockets nuevos (el único `bind` es el del DNS ya existente),
  ni `connect`, ni IPs aparte de 192.168.4.1, ni rutas nuevas en el HTTP, ni comandos, ni
  escrituras en la NVS, ni nuevas llamadas a `esp_restart`. `portal_origen`, `portal_lectura` y
  `conectividad_sta` son funciones puras de 10-13 líneas.
- **CI:** las únicas descargas siguen siendo las de antes (gitleaks y el runner, con sha256; la
  comprobación de `TESTBENCH_URL` en `verify`). No hay secretos nuevos ni `curl | sh`. El job
  `verify` mantiene la condición de tag y propietario.
- **Evidencias (`test-results/`):** son logs y HTML de las ejecuciones. No revisé línea a línea
  si contienen datos de la casa: el hook pre-push con gitleaks y la lista de patrones lo
  cubren, y por las reglas de esta verificación no comparé contra `.env`. **Por verificar** si
  se quiere una comprobación independiente.
- **Veredicto:** sin indicios de puerta trasera ni de cambios ajenos a los hallazgos.

## Veredicto global

**Sí, se puede cerrar la puerta S1**, con dos salvedades que el propietario debería decidir
explícitamente.

Motivos:
1. Todos los criterios de §3.5 se cumplen tal como están escritos: FR-POR-08/09/10, FR-CON-07,
   T24 y T25 con sus pruebas, regresiones de banco en verde, CI de SEC-08 y SEC-09 en verde, y
   SEC-10/11 como requisitos de la Fase 3. No hay nada crítico ni alto pendiente, ni ninguna
   regresión del portal o de la conectividad.
2. Los problemas que quedan son de severidad **baja**, exigen estar dentro del alcance del AP
   abierto o en la LAN durante VALIDANDO, y en el peor caso dan una denegación de servicio del
   aprovisionamiento. Ninguno da más acceso que el que ya se acepta en §19.1 (c): configurar el
   nodo durante la ventana.

Salvedades:
- **SEC-05 (cliente lento) y N-02:** la corrección no cumple la intención del hallazgo. Lo
  recomendable es añadir un plazo total al POST antes de la Fase 3: es un cambio pequeño y
  aislado, con su prueba de host. Si no, registrarlo como riesgo aceptado en §19.3.
- **SEC-06 (host débil de lwIP) y N-01 (parada del DNS):** por verificar contra la lwIP de
  ESP-IDF 6.0.2. Si se confirman, corregirlos o registrarlos en §19.3. TC-POR-12 debería
  comprobar también que el DNS se detiene de verdad.
- Por verificar fuera de este repositorio: la correspondencia SHA ↔ versión de las acciones y
  el digest de la imagen, y el primer `gh release create` real.
