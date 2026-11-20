# Borrador: alertas de Home Assistant para el nodo clima (H3 y H4, H-94) — para revisar

El firmware no emite alertas (FSD, historial 0.9.0): las saca Home Assistant de lo que el nodo publica. Este
borrador cubre los huecos H3 y H4 de `testing/analisis-cortes-parciales.md`. **No está instalado ni probado.**
Es para que el propietario lo revise. Los marcadores `<sitio>`, `<zona>` y `<nodo>` se cambian en la instalación,
nunca en el repo. `<nodo>` es `clima-xxxxxx`.

## Qué publica el nodo y qué usa cada alerta

- `homeassistant/sensor/<nodo>/…/config`: las tres medidas, por Discovery, con disponibilidad por `status`
  (`online` y `offline`).
- `<sitio>/<zona>/<nodo>/status`, retenido, QoS 1: `estado`, `fw`, `rssi`, `reset`, `uptime_s`, `lecturas`,
  `err_sensor`, `ota` y `hora_valida` (§9.3). Si el nodo se cae, el broker lo reemplaza por el Last Will
  `{"estado":"offline"}` en ≤ 100 s.
- `status` **no** va por Discovery. Para las alertas A3 a A7 hace falta un sensor MQTT que lo lea, en
  `configuration.yaml`:

```yaml
mqtt:
  sensor:
    - name: "Clima <zona> estado"
      unique_id: "<nodo>_estado"
      state_topic: "<sitio>/<zona>/<nodo>/status"
      value_template: "{{ value_json.estado }}"
      json_attributes_topic: "<sitio>/<zona>/<nodo>/status"
```

## Alertas propuestas (H3)

| ID | Condición | Por qué | Gravedad |
|---|---|---|---|
| A1 | `estado` = `offline` durante 2 min | Nodo caído, sin Wi-Fi o sin broker (LWT) | Alta |
| A2 | La temperatura no se actualiza en 3 min, aunque el nodo esté `online` | Medidas que no llegan (pérdida de paquetes, sensor colgado) | Alta |
| A3 | `hora_valida` = false durante 1 h | Sin SNTP: sin Internet o sin DNS. Las medidas siguen llegando, pero sin `ts` | Baja |
| A4 | `reset` cambia a `brownout`, `panic`, `task_wdt`, `int_wdt` o `wdt` | Fuente floja, fallo o watchdog | Media |
| A5 | `uptime_s` baja respecto del valor anterior | Reinicio del nodo, cualquiera que sea la causa | Media; alta si son más de 3 en 1 h (bucle) |
| A6 | `rssi` < −80 dBm durante 15 min | Señal débil: anuncia cortes intermitentes | Baja |
| A7 | `err_sensor` sube | Lecturas del SHT41 inválidas | Media |

```yaml
automation:
  - alias: "Clima <zona>: nodo offline"                      # A1
    triggers:
      - trigger: state
        entity_id: sensor.clima_<zona>_estado
        to: "offline"
        for: "00:02:00"
    actions:
      - action: script.aviso_clima
        data: {nivel: alta, texto: "Nodo clima <zona> sin conexión desde hace 2 min"}

  - alias: "Clima <zona>: sin medidas"                       # A2
    triggers:
      - trigger: time_pattern
        minutes: "/1"
    conditions:
      - condition: state
        entity_id: sensor.clima_<zona>_estado
        state: "online"
      - condition: template
        value_template: >
          {{ (now() - states.sensor.clima_<zona>_temperatura.last_updated).total_seconds() > 180 }}
    actions:
      - action: script.aviso_clima
        data: {nivel: alta, texto: "Nodo clima <zona> conectado pero sin medidas desde hace 3 min"}

  - alias: "Clima <zona>: sin hora de red"                   # A3
    triggers:
      - trigger: template
        value_template: "{{ state_attr('sensor.clima_<zona>_estado', 'hora_valida') == false }}"
        for: "01:00:00"
    actions:
      - action: script.aviso_clima
        data: {nivel: baja, texto: "Nodo clima <zona> sin hora de red desde hace 1 h (¿Internet o DNS?)"}

  - alias: "Clima <zona>: reinicio anómalo"                  # A4 y A5
    triggers:
      - trigger: state
        entity_id: sensor.clima_<zona>_estado
        attribute: uptime_s
    conditions:
      - condition: template
        value_template: >
          {{ trigger.from_state is not none and trigger.to_state.attributes.uptime_s is number
             and trigger.from_state.attributes.uptime_s is number
             and trigger.to_state.attributes.uptime_s < trigger.from_state.attributes.uptime_s }}
    actions:
      - action: script.aviso_clima
        data:
          nivel: >
            {{ 'media' if trigger.to_state.attributes.reset in
               ['brownout','panic','task_wdt','int_wdt','wdt'] else 'baja' }}
          texto: "Nodo clima <zona> se reinició (reset = {{ trigger.to_state.attributes.reset }})"

  - alias: "Clima <zona>: señal débil"                       # A6
    triggers:
      - trigger: numeric_state
        entity_id: sensor.clima_<zona>_estado
        attribute: rssi
        below: -80
        for: "00:15:00"
    actions:
      - action: script.aviso_clima
        data: {nivel: baja, texto: "Nodo clima <zona> con señal Wi-Fi débil (< −80 dBm) desde hace 15 min"}

  - alias: "Clima <zona>: errores del sensor"                # A7
    triggers:
      - trigger: state
        entity_id: sensor.clima_<zona>_estado
        attribute: err_sensor
    conditions:
      - condition: template
        value_template: >
          {{ trigger.from_state is not none and trigger.to_state.attributes.err_sensor is number
             and trigger.from_state.attributes.err_sensor is number
             and trigger.to_state.attributes.err_sensor > trigger.from_state.attributes.err_sensor }}
    actions:
      - action: script.aviso_clima
        data: {nivel: media, texto: "Nodo clima <zona>: lecturas inválidas del sensor"}
```

La A5 de bucle (más de 3 reinicios en 1 h) necesita un contador (`counter` que se pone a cero cada hora). Se deja
para la revisión.

## Aviso que no dependa de la nube (H4)

Un único script `aviso_clima` reparte cada alerta por dos vías. La local siempre funciona; la de la nube, solo si
hay Internet:

```yaml
script:
  aviso_clima:
    fields:
      nivel: {description: "alta | media | baja"}
      texto: {description: "mensaje"}
    sequence:
      - action: persistent_notification.create          # local: se ve en HA aunque no haya Internet
        data: {title: "Clima ({{ nivel }})", message: "{{ texto }}"}
      - action: logbook.log                             # rastro local
        data: {name: "Clima", message: "{{ texto }}"}
      - continue_on_error: true                         # nube: puede fallar sin Internet
        action: notify.notify                           # servicio de aviso del teléfono (el que ya use la villa)
        data: {title: "Clima ({{ nivel }})", message: "{{ texto }}"}
```

Propuestas para revisar:

- **Reintento al volver Internet:** si `notify.notify` falló, reenviar las alertas pendientes cuando HA vuelva a
  tener Internet. Por ejemplo, con un `input_text` que guarde la última alerta no entregada.
- **Vía local activa** para las alertas altas, si la villa tiene con qué: un altavoz o una pantalla de HA en la
  casa, o un aviso por la red local a un equipo siempre encendido.
- **Alerta de «HA sin Internet»:** que HA avise localmente cuando pierde la salida (por ejemplo, con un `ping`
  periódico a una IP pública). Así se distingue «el nodo está bien pero el aviso no salió».

## Cómo se probaría (después de revisarlo)

En el HA de prueba (`scripts/ha/ha_prueba.py`), con el banco: A1 (corte del AP y del broker), A2 (pérdida, cuando
exista CR-TB-25), A3 (`bench-sntp-block` y un reinicio), A4/A5 (reset por la línea del banco y `wdt-test` de la
imagen de banco), A6 (no se puede bajar el RSSI en el banco: queda para campo) y A7 (SDA suelto, con operador).
