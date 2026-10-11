# Nodo Clima Piloto — Manual de usuario

Cómo instalar y operar el nodo. Son procedimientos para personas, en presente.
El FSD dice qué hace el sistema; este manual, cómo hacer que lo haga.

**Estado: todavía no hay nada desplegable.** No existe firmware. Los capítulos
se llenan a medida que cada fase del FSD (§3) se completa.

## Contenido

1. Qué necesitas
2. Montaje
3. Primer flasheo
4. Aprovisionamiento por el portal
5. Ver los datos en Home Assistant
6. Actualizar por OTA
7. Solución de problemas
8. Recuperación

## 1. Qué necesitas

- ESP32-S3-DevKitC-1 **N8R8** y un breakout SHT41 (dirección 0x44).
- Cable USB-C de datos y un PC con el entorno del proyecto (devcontainer).
- Un broker MQTT en la LAN (p. ej., el add-on Mosquitto de Home Assistant) con
  usuario y contraseña. Las credenciales las guardas tú y nunca van al
  repositorio.

## 2. Montaje

SHT41 → DevKitC-1: VDD → 3V3, GND → GND, SDA → GPIO8, SCL → GPIO9 (pines
pendientes de aceptar: FSD D1). Separa el sensor al menos 5 cm de la placa: el
calor del ESP32 falsea la temperatura.

## 3. Primer flasheo

*Pendiente (Fase 1).*

## 4. Aprovisionamiento por el portal

*Pendiente (Fase 1).* Resumen del comportamiento: un nodo sin configuración
emite el Wi-Fi abierto `clima-xxxxxx`; al unirte, el teléfono abre el portal.
Introduce el Wi-Fi, el broker y la zona (minúsculas, cifras, `_` o `-`). Si el
nodo consigue unirse, el Wi-Fi `clima-xxxxxx` desaparece; si no, vuelve a
mostrar el formulario con el error.

## 5. Ver los datos en Home Assistant

*Pendiente (Fase 2).*

## 6. Actualizar por OTA

*Pendiente (Fase 3).*

## 7. Solución de problemas

| Síntoma | Causa | Arreglo |
|---|---|---|
| *(se añaden filas a medida que aparecen fallos reales)* | | |

## 8. Recuperación

- **Automática.** Los cortes de Wi-Fi o de broker se recuperan solos, sin
  reiniciar el nodo. Una OTA mala vuelve sola a la versión anterior en ≤ 5 min.
- **Manual: reaprovisionar** (cambio de Wi-Fi, broker o zona). Borra la NVS por
  USB (comando pendiente, Fase 1); el nodo vuelve a abrir el portal.

---

**Contrato:** `docs/Functionality/FSD-nodo-clima.md` · **Reglas de build:**
`docs/Method/AI-Workflow.md`
