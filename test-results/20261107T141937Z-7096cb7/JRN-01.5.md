# JRN-01.5 — Home Assistant descubre el nodo

- Home Assistant de prueba 2026.10.4 en la laptop (Docker de WSL, H-52), instancia nueva

- Arrancar el broker, borrar los retenidos de Discovery y añadir la integración MQTT a Home Assistant
- Resetear el DUT y levantar el AP; esperar T11 y el dispositivo en Home Assistant
- Parar el broker 10 s y arrancarlo; esperar T11
- Resetear el DUT; esperar T11
- log: `JRN-01.5-serie.log` (418 líneas)

## Resultado

- conexión: 1 dispositivo(s) MQTT; «Clima sitio1 zona1»: sensor.clima_sitio1_zona1_temperatura=30.3 °C, sensor.clima_sitio1_zona1_humedad=64.7 %, sensor.clima_sitio1_zona1_punto_de_rocio=23.0 °C
- broker parado y arrancado: 1 dispositivo(s) MQTT; «Clima sitio1 zona1»: sensor.clima_sitio1_zona1_temperatura=30.3 °C, sensor.clima_sitio1_zona1_humedad=64.7 %, sensor.clima_sitio1_zona1_punto_de_rocio=23.0 °C
- DUT reiniciado: 1 dispositivo(s) MQTT; «Clima sitio1 zona1»: sensor.clima_sitio1_zona1_temperatura=30.3 °C, sensor.clima_sitio1_zona1_humedad=65.1 %, sensor.clima_sitio1_zona1_punto_de_rocio=23.0 °C

**Resultado: PASS** — 1 dispositivo «Clima sitio1 zona1» con 3 entidades en °C/% tras conectar, tras el broker y tras el reset
