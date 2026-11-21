# Borrador: alertas de Home Assistant para los nodos clima (H3 y H4, H-94) — revisión 2

**Revisión 2** (propietario, 2026-11-21): gravedad baja y 15 min para A1 y A2; las alertas del clima van a un
resumen y solo las de agua y seguridad avisan al instante; sin Internet, el aviso lo da el vigilante externo del
hub (FR-VIG-01, H-93); el canal del teléfono es WhatsApp; y en lugar de automatizaciones copiadas, una plantilla
(blueprint) por nodo.

El firmware no emite alertas (FSD, historial 0.9.0): las saca Home Assistant de lo que el nodo publica. **Este
documento no está instalado ni probado.** Los marcadores `<sitio>`, `<zona>` y `<nodo>` se cambian en la
instalación, nunca en el repo.

## Lo que usa la plantilla

- **Medidas:** `temperatura`, `humedad` y `punto_rocio`, por Discovery, con disponibilidad por `status`.
- **`status`** (`<sitio>/<zona>/<nodo>/status`, retenido): `estado`, `fw`, `rssi`, `reset`, `uptime_s`,
  `lecturas`, `err_sensor`, `ota` y `hora_valida` (§9.3). Si el nodo se cae, el broker lo reemplaza por el Last
  Will `{"estado":"offline"}` en ≤ 100 s.
- **Un sensor MQTT por nodo que lea `status`**, porque `status` no va por Discovery. Va en `configuration.yaml`:

```yaml
mqtt:
  sensor:
    - name: "Clima <zona> estado"
      unique_id: "<nodo>_estado"
      state_topic: "<sitio>/<zona>/<nodo>/status"
      value_template: "{{ value_json.estado }}"
      json_attributes_topic: "<sitio>/<zona>/<nodo>/status"
```

## Alertas (todas de gravedad baja: el nodo clima no es crítico)

| ID | Condición | Por qué |
|---|---|---|
| A1 | `estado` = `offline` durante **15 min** | Nodo caído, sin Wi-Fi o sin broker (LWT) |
| A2 | Sin medida de temperatura en **15 min** con el nodo `online` | Medidas que no llegan |
| A3 | `hora_valida` = false durante 1 h | Sin SNTP (Internet o DNS); las medidas siguen sin `ts` |
| A4 | Reinicio con `reset` en {brownout, panic, task_wdt, int_wdt, wdt} | Fuente floja, fallo o watchdog |
| A5 | Cualquier reinicio (`uptime_s` baja) | Reinicios en general; un bucle se ve en el resumen |
| A6 | `rssi` < −80 dBm durante 15 min | Señal débil que anuncia cortes |
| A7 | `err_sensor` sube | Lecturas del SHT41 inválidas |

**Ninguna avisa al instante.** Todas van al resumen de la casa. Los avisos al instante quedan para los sistemas de
agua y de seguridad, que no son de este documento.

## Plantilla (blueprint) `nodo_clima_alertas.yaml`

Una sola plantilla. Cada nodo es una automatización creada desde ella, con sus tres entidades y su zona. Se
guarda en `blueprints/automation/villa/nodo_clima_alertas.yaml`.

```yaml
blueprint:
  name: Nodo clima — alertas al resumen
  description: >
    Alertas de gravedad baja de un nodo clima (A1–A7). No avisan al instante: dejan cada alerta en el resumen de
    la casa con la acción «Añadir al resumen». Sin Internet, el aviso lo da el vigilante externo del hub
    (FR-VIG-01, H-93), no esta plantilla.
  domain: automation
  input:
    zona:
      name: Zona
      selector: {text: {}}
    estado:
      name: Sensor de status del nodo
      description: El sensor MQTT que lee <sitio>/<zona>/<nodo>/status, con sus atributos
      selector: {entity: {domain: sensor}}
    temperatura:
      name: Sensor de temperatura del nodo
      selector: {entity: {domain: sensor}}
    al_resumen:
      name: Añadir al resumen
      description: Acción que añade una línea al resumen de la casa (recibe las variables «zona» y «texto»)
      selector: {action: {}}

mode: queued
max: 10

trigger_variables:
  temperatura: !input temperatura

triggers:
  - trigger: state                                   # A1
    id: a1
    entity_id: !input estado
    to: "offline"
    for: "00:15:00"
  - trigger: template                                # A2: dispara una vez al pasar el umbral
    id: a2
    value_template: >
      {{ states[temperatura] is not none and
         (now() - states[temperatura].last_updated).total_seconds() > 900 }}
  - trigger: state                                   # A3
    id: a3
    entity_id: !input estado
    attribute: hora_valida
    to: false
    for: "01:00:00"
  - trigger: state                                   # A4 y A5
    id: a45
    entity_id: !input estado
    attribute: uptime_s
  - trigger: numeric_state                           # A6
    id: a6
    entity_id: !input estado
    attribute: rssi
    below: -80
    for: "00:15:00"
  - trigger: state                                   # A7
    id: a7
    entity_id: !input estado
    attribute: err_sensor

variables:
  zona: !input zona
  estado_ent: !input estado
  nuevo: "{{ trigger.to_state.attributes if trigger.to_state is defined and trigger.to_state else {} }}"
  viejo: "{{ trigger.from_state.attributes if trigger.from_state is defined and trigger.from_state else {} }}"
  texto: >
    {% if trigger.id == 'a1' %}sin conexión desde hace 15 min
    {% elif trigger.id == 'a2' %}conectado pero sin medidas desde hace 15 min
    {% elif trigger.id == 'a3' %}sin hora de red desde hace 1 h (¿Internet o DNS?)
    {% elif trigger.id == 'a45' %}se reinició (reset = {{ nuevo.reset }})
    {% elif trigger.id == 'a6' %}señal Wi-Fi débil (< −80 dBm) desde hace 15 min
    {% else %}lecturas inválidas del sensor (err_sensor = {{ nuevo.err_sensor }}){% endif %}

conditions:
  - condition: template                              # A2 solo con el nodo online (si no, ya avisa A1)
    value_template: "{{ trigger.id != 'a2' or states(estado_ent) == 'online' }}"
  - condition: template                              # A4/A5 solo si uptime_s bajó de verdad
    value_template: >
      {{ trigger.id != 'a45' or (nuevo.uptime_s is number and viejo.uptime_s is number
                                  and nuevo.uptime_s < viejo.uptime_s) }}
  - condition: template                              # A7 solo si err_sensor subió
    value_template: >
      {{ trigger.id != 'a7' or (nuevo.err_sensor is number and viejo.err_sensor is number
                                 and nuevo.err_sensor > viejo.err_sensor) }}

actions:
  - action: logbook.log                              # rastro local en HA
    data: {name: "Clima {{ zona }}", message: "{{ texto }}"}
  - choose: []
    default: !input al_resumen
```

Notas de la plantilla:

- `al_resumen` recibe las variables `zona` y `texto`. La acción concreta depende de cómo esté hecho el resumen de
  la casa: por ejemplo, añadir una tarea a una lista `todo` o una línea a un `input_text`. Se decide con el resumen.
- A4 y A5 van en un solo disparador. El texto lleva el valor de `reset`, así un brownout o un watchdog se
  distinguen en el resumen sin una alerta aparte.

## Canal al teléfono: WhatsApp (decisión base)

- **El resumen sale por WhatsApp**, a la hora o con la frecuencia que fije el resumen de la casa. Es un envío para
  toda la casa, no uno por nodo, y lo hace la automatización del resumen, no esta plantilla.
- **El aviso inmediato por WhatsApp** queda para agua y seguridad.

## Sin Internet: el vigilante externo del hub (FR-VIG-01, H-93)

- Con la casa vacía, una notificación local de HA no la ve nadie. **El aviso de «casa sin Internet» lo da el
  vigilante externo del hub** (FR-VIG-01, 15 min, aprobado en H-93 para AGUA). Es uno solo para toda la casa, y
  esta plantilla no lo duplica.
- Mientras falte Internet, las alertas del clima siguen en el `logbook` y en el resumen pendiente. Salen por
  WhatsApp con el siguiente resumen, cuando vuelva la conexión.

## Pendiente de decisión del propietario

- **Segundo canal por SMS con un módem 4G en la Pi**, para avisar sin depender de Internet ni de WhatsApp. No se
  propone para el clima, que es de gravedad baja; sería para agua y seguridad, y para el propio vigilante. Hay que
  decidir el módem, el plan de datos y SMS, y qué alertas lo usan.

## Cómo se probaría (después de aprobarlo)

En el HA de prueba (`scripts/ha/ha_prueba.py`), con la plantilla y una acción `al_resumen` que escriba en una lista:

| Alerta | Cómo se provoca |
|---|---|
| A1 | Corte del AP y del broker más de 15 min |
| A2 | Pérdida de paquetes, cuando exista CR-TB-25 |
| A3 | `bench-sntp-block` y un reinicio |
| A4 y A5 | Reset por la línea del banco, y `wdt-test` de la imagen de banco |
| A6 | No se puede en el banco: queda para campo |
| A7 | SDA suelto, con operador |
