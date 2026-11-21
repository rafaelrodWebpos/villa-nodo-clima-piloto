# Cortes parciales: qué hace el nodo y qué falta probar (análisis del 2026-11-20)

Base: FSD 0.9.11, firmware `main` (ESP-IDF 6.0.3) y banco villa-2 `6dffd70`. Es un análisis para decidir; el FSD y
las puertas no cambian sin aprobación del propietario.

## Cómo es el nodo (lo que condiciona todo lo demás)

- **El broker está en la LAN.** Las medidas no necesitan Internet: van al broker de Home Assistant. Internet solo
  hace falta para SNTP (`pool.ntp.org`, por DNS) y para la OTA (GitHub).
- **Alertas:** el firmware no emite ninguna (FSD, historial 0.9.0). Home Assistant las saca de lo que publica el
  nodo:
  - el Last Will `{"estado":"offline"}`, retenido, en ≤ 100 s (FR-MQTT-05; keepalive de 60 s);
  - los campos de `status`: `rssi`, `reset`, `uptime_s`, `lecturas`, `err_sensor` y `hora_valida`.
- **Recuperación:** nunca hay reinicio por pérdida de red (FR-CON-01). Los reintentos van con backoff de 1 s a 60 s
  (FR-CON-02). Tras volver el AP, una medida en ≤ 90 s (FR-CON-03); tras volver el broker, en ≤ 75 s y sin
  desasociarse (FR-CON-04).
- **Sin búfer offline** (rechazado por el usuario): una medida que no se puede publicar se pierde. Las medidas van
  con QoS 0 y retenidas; `status` va con QoS 1.
- **Una sola red guardada:** el nodo no salta a otra red; solo reconecta al mismo SSID, a cualquier punto del mesh.
- **Hora:** sin hora válida publica sin `ts` y con `hora_valida = false` (FR-TIME-03). Una resincronización
  fallida no invalida una hora ya buena (FR-TIME-04).
- **Energía:** el detector de bajo voltaje (brownout) está activo, nivel 7 (el defecto de ESP-IDF). Si salta, el
  nodo se reinicia y `status.reset` dice `brownout`.
- **Lo que hoy no cubre el firmware:**
  - No atiende `IP_EVENT_STA_LOST_IP` (main.c solo escucha `STA_DISCONNECTED` y `STA_GOT_IP`).
  - Asociado sin IP, no hay plazo ni reasociación: depende de que el cliente DHCP de lwIP siga reintentando.

## (a) Internet parcial (Wi-Fi y LAN arriba)

| Caso | Qué detecta el nodo | Qué sigue funcionando | Qué alerta sale | Cómo se recupera solo | ¿Prueba de banco? |
|---|---|---|---|---|---|
| Sin salida a Internet | Nada directo. SNTP falla (`sntp:` reintenta) y la OTA da `error:red`/`tls` | Todo: medidas, `status` y HA (broker en la LAN) | Ninguna si ya tenía hora. Tras un reinicio sin Internet, `hora_valida = false` (solo si HA lo vigila) | Sí: SNTP reintenta (FR-TIME-06) y la hora vuelve sola | Sí: TC-TIME-05 y 06 (AP sin salida) |
| DNS que falla (Internet arriba) | SNTP no resuelve el pool. **Si `mqtt_host` es un nombre, MQTT no conecta** | Con el broker por IP, todo menos SNTP y OTA. Con el broker por nombre, nada se publica | Con el broker por nombre: LWT offline → HA lo marca no disponible | Sí, cuando vuelve el DNS (backoff de MQTT ≤ 60 s) | **Parcial:** `dns_override` desvía un nombre; no hay «DNS que no contesta» |
| Pérdida de paquetes o enlace intermitente | No lo mide. Desconexiones de MQTT por keepalive y `wifi_down` si cae la asociación | Lo que logra pasar. Las medidas QoS 0 perdidas no se reenvían | Si el silencio supera ~90 s: LWT offline y online otra vez (parpadeo en HA) | Sí: backoff y reconexión | **No** (hace falta inyectar pérdida o retardo) |
| WhatsApp o la nube caídos con Internet arriba | Nada: el nodo no usa la nube | Todo en el nodo | **El aviso al teléfono no llega**, porque depende de HA y de la nube | Lo que haga HA | No aplica al nodo (es de HA) |

## (b) Red parcial

| Caso | Qué detecta el nodo | Qué sigue funcionando | Qué alerta sale | Cómo se recupera solo | ¿Prueba de banco? |
|---|---|---|---|---|---|
| Deco principal sin Internet, LAN bien | Como en (a): solo SNTP y OTA | Todo lo local | Ninguna (o `hora_valida` tras un reinicio) | Sí | Sí (sin salida a Internet) |
| Satélite del mesh apagado | `wifi_down` (desasociación), backoff | Medidas sin publicar mientras no reasocia | LWT offline si tarda más de ~90 s | Sí: reconecta al mismo SSID por otro nodo del mesh, si llega la señal; ≤ 90 s (FR-CON-03) | **Parcial:** AP apagado sí (TC-CON-10/11); cambio de punto de acceso no (el banco tiene una sola radio) |
| Satélite encendido pero con el enlace al principal roto | **Nada de Wi-Fi:** sigue asociado. MQTT falla y reintenta para siempre | Nada se publica | LWT offline | **No, hasta que se arregle el satélite:** el nodo no se reasocia a otro punto del mesh mientras el Wi-Fi siga arriba (FR-CON-04 lo pide así cuando vuelve el broker) | **No:** falta un «agujero negro» (DROP) hacia el broker; parar el broker da un RST, que es otro caso |
| Switch apagado con la Pi o HA encendidos | Igual que el caso anterior, o broker inalcanzable | Nada se publica | LWT offline, si el broker sigue vivo para emitirlo; si no, HA no ve nada | Sí, al volver: ≤ 75 s (FR-CON-04) | Sí, como broker caído (TC-CON-08/12, TC-MED-02); la variante DROP no |
| DHCP caído (AP arriba) | **Ningún evento:** asociado sin IP; se queda en CONECTANDO_WIFI sin plazo | Nada se publica | LWT offline (o ningún status, si no había conectado) | Probable: el cliente DHCP de lwIP sigue pidiendo. **No está especificado ni probado** | **No** (hace falta apagar el DHCP con el AP arriba) |
| Se acaba el contrato DHCP y no se renueva | lwIP quita la IP a los 120 s (`IP_LOST_TIMER`), pero **main no escucha `LOST_IP`**: el estado sigue creyendo que hay Wi-Fi | Nada se publica | LWT offline | Probable al volver el DHCP (`GOT_IP` otra vez). **No probado** | **No** |
| Saltar a otra red guardada | No puede: una sola red en NVS | — | — | — (a diferencia de la laptop de AGUA, el nodo no salta a «Android») | No aplica |

## (c) Energía parcial

| Caso | Qué detecta el nodo | Qué sigue funcionando | Qué alerta sale | Cómo se recupera solo | ¿Prueba de banco? |
|---|---|---|---|---|---|
| Bajo voltaje y caídas breves | Brownout → reinicio con `reset = brownout`. Si es corto, puede ser `poweron` | Nada durante el reinicio. Primera medida en ≤ 30 s (FR-CON-05) | LWT offline si dura más de ~90 s. Un `reset` distinto o un `uptime_s` bajo solo se ven si HA los vigila | Sí. **Un bucle de brownouts (fuente floja) no tiene alerta propia** | **No** (el banco no regula la tensión; el corte del USB-C es total) |
| Pérdida de una fase | Igual que un corte total para lo que esté en esa fase | Lo que esté en otra fase | Según qué cayó: la tabla (d) | Igual que (d) | Parcial: cortes manuales del USB-C |
| UPS para unos equipos y no para otros | Según qué quede vivo: nodo sin Wi-Fi, o Wi-Fi sin broker | Lo que tenga UPS | Si HA y el broker tienen UPS y el nodo no: LWT. Si el nodo tiene energía y el Deco no: LWT por keepalive | Sí, ver (d) | Parcial |
| Regreso en distinto orden | Ver (d) | — | — | — | — |

## (d) Combinados, sobre todo el orden de regreso tras un apagón

| Orden de regreso | Qué hace el nodo | Cota del FSD | ¿Prueba de banco? |
|---|---|---|---|
| El nodo vuelve antes que el Deco | Backoff de Wi-Fi hasta 60 s; sin hora (RTC perdido) | Medida en ≤ 90 s desde el AP (FR-CON-03) | **No en ese orden:** hay cortes con el AP arriba y AP apagado con el nodo encendido, pero no reinicio con el AP abajo |
| Deco antes que HA o el broker | Wi-Fi bien, MQTT con backoff | ≤ 75 s desde el broker (FR-CON-04) | **No en ese orden** |
| Todo de vuelta, Internet tarde | Publica sin `ts` y con `hora_valida = false` hasta que SNTP responda | FR-TIME-03/05/06 | Sí, en partes (TC-TIME-05/06) |
| Deco de vuelta pero DHCP tarde | Asociado sin IP (ver b) | No especificado | No |
| Bajo voltaje repetido mientras falla la red | Brownouts y backoffs que vuelven a empezar | No especificado | No |

## Huecos y propuestas

Tipo: **F** = firmware/FSD (necesita aprobación), **HA** = Home Assistant (fuera del firmware), **B** = capacidad
nueva del banco (fork; el número CR-TB lo da el propietario), **T** = prueba nueva con lo que el banco ya tiene,
**M** = método del Harness.

| # | Hueco | Riesgo | Propuesta | Tipo | Prioridad |
|---|---|---|---|---|---|
| H1 | El firmware no atiende `STA_LOST_IP` ni pone plazo a «asociado sin IP» | Nodo mudo sin causa visible hasta que vuelva el DHCP | Tratar `LOST_IP` como `wifi_down` (T08 inversa) y poner un plazo (por ejemplo 60 s sin IP → reasociar). Fila nueva en la tabla de estados | F | Alta |
| H2 | Con el Wi-Fi arriba y el broker inalcanzable mucho tiempo, nunca se reasocia (satélite con el enlace roto) | Nodo caído hasta que alguien arregle el satélite, aunque haya otro punto del mesh | Tras N min sin broker con el Wi-Fi arriba (por ejemplo 10), reasociar el Wi-Fi una vez, sin reiniciar. Es compatible con FR-CON-01; FR-CON-04 necesita una aclaración | F | Media |
| H3 | No hay un conjunto de alertas definido en HA | Casos parciales (sin hora, brownouts, señal débil, parpadeo) que nadie ve | Definir y probar en el HA de prueba: LWT offline > 2 min; sin medida > 3 min; `hora_valida = false` > 1 h; `reset` en {brownout, panic, task_wdt, int_wdt}; `uptime_s` que baja (reinicios); `rssi` < −80 dBm sostenido | HA | Alta |
| H4 | El aviso al teléfono depende de la nube (WhatsApp, app) | Con Internet caído no llega ninguna alerta, justo cuando más falta hace | Una alerta local en HA (notificación persistente o tablero) y, si se quiere, una vía que no use Internet | HA | Media |
| H5 | `status` no cuenta reconexiones | El parpadeo y la pérdida de paquetes no se ven en los datos | Campos opcionales `reconexiones_wifi` y `reconexiones_mqtt` en §9.3 | F | Baja |
| H6 | Broker por nombre: un DNS caído tumba el nodo | Todo el nodo depende del DNS | La guía de instalación ya recomienda IP (SEC-02); comprobarlo en la instalación (S2) | M | Media |
| H7 | Un bucle de brownouts no tiene alerta ni prueba | Fuente floja que reinicia en bucle sin que nadie se entere | La alerta de H3 (`reset = brownout`). En el banco solo se puede con una fuente regulable; si no, queda como prueba de campo | HA / B | Baja |
| H8 | Falta «agujero negro» hacia el broker (DROP, no RST) | Distinto comportamiento de TCP: los timeouts largos no están probados | Capacidad `bench-broker-blackhole`: regla DROP en el puerto 1883 solo para el DUT. El skill testbench-mqtt ya describe DROP y REJECT | B | Media |
| H9 | No se puede apagar solo el DHCP | H1 no se puede probar | Capacidad `bench-dhcp-off`: dnsmasq sin DHCP con el AP arriba, y contratos cortos para probar `LOST_IP` | B | Alta (junto con H1) |
| H10 | No hay inyección de pérdida ni de retardo | (a) intermitente sin probar | Capacidad `bench-netem`: `tc netem` en la interfaz del AP, con pérdida %, retardo y cortes intermitentes | B | Media |
| H11 | No hay «DNS que no contesta» | (a) DNS caído sin probar | Ampliar `dns_override`: modo «sin respuesta» o NXDOMAIN para un nombre o para todos | B | Baja |
| H12 | Orden de regreso tras un apagón sin probar | (d) | Prueba nueva con lo que hay: reinicio del DUT con el AP apagado, AP a los 3 min y broker a los 6 min; medir FR-CON-03/04 desde cada regreso. Con reset por la línea del banco, sin operador | T | Alta |
| H13 | Cambio de punto de acceso del mesh | (b) satélite apagado | El banco tiene una sola radio: prueba de campo en la villa (S2), apagando un satélite | M | Media |
| H14 | El método no pide fallos parciales | Los planes solo tienen cortes totales | Añadir a `docs/Method/standards/testing.md` una «matriz de fallos parciales» (internet, DNS, DHCP, pérdida, orden de regreso, energía) que cada proyecto revise con su FSD | M | Media |

## Propuesta de orden

1. **Ya, sin banco ni FSD:**
   - H12 como prueba nueva, que corre en la próxima regresión;
   - H3 y H4 como definición de alertas de HA para revisar;
   - H14 en el método.
2. **Siguiente ronda del FSD** (con aprobación): H1, H2 y, si se quiere, H5.
3. **Siguiente ronda del fork** (junto con L-1…L-5 y T-1): H9, H8, H10 y H11, con sus números CR-TB.
4. **En la instalación (S2):** H6 y H13 en campo.

## Decisión del propietario (H-94, 2026-11-20)

1. **Ya, sin banco:**
   - H12 como TC-CON-15 (`dca7f93`, en la tanda E de la regresión);
   - borrador de las alertas de HA (H3 y H4) en `testing/borrador-alertas-ha.md`, para revisar;
   - H14, la matriz de fallos parciales en `docs/Method/standards/testing.md`.
2. **Próxima ronda del FSD:** H1 y H2.
3. **Próxima ronda del fork** (junto con L-1…L-5 y T-1), con estos números del propietario:
   - CR-TB-23: H8, agujero negro hacia el broker;
   - CR-TB-24: H9, DHCP apagado;
   - CR-TB-25: H10, pérdida y retardo;
   - CR-TB-26: H11, DNS que no contesta.
4. **En la instalación (S2):** broker por IP (H6) y apagar un satélite en campo (H13).

- **Revisión del borrador de alertas** (propietario, 2026-11-21): A1 y A2 con gravedad baja y 15 min; las alertas
  del clima van a un resumen; sin Internet avisa el vigilante externo del hub (FR-VIG-01, H-93); el canal es
  WhatsApp; y una plantilla (blueprint) por nodo. Queda pendiente de decisión el segundo canal por SMS con un
  módem 4G en la Pi.
