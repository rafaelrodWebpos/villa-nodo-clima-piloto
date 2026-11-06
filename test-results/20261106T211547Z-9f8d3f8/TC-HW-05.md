# TC-HW-05 — Escaneo del bus I²C del SHT41

- Precondiciones: construir la sonda tests/target/i2c_probe con ESP-IDF
- Grabar la sonda en SLOT1 y capturar su arranque
- log: `TC-HW-05-sonda.log` (66 líneas)
- Restaurar la imagen de la CI del commit bajo prueba

## Resultado

- `i2c: scan sda=8 scl=9 hz=100000 ack=0x44`
- `i2c: scan sda=8 scl=9 hz=100000 ack=0x44`
- el que cuenta (pull-ups externos): `I (328) i2c: scan sda=8 scl=9 hz=100000 ack=0x44`

**Resultado: PASS** — escaneo con pull-ups externos: ack=0x44
