# Pendientes del propietario

Tareas que necesitan una decisión o una acción física del propietario. Cada entrada
lleva el contexto y las opciones; cuando se resuelve, se marca con la fecha y lo decidido.

## 2026-11-07 · FR-SEN-03 — desconectar y reconectar SDA (acción física)

- **Contexto.** Tarea 3 de la lista H-64. El contrato de FR-SEN-03 pide desconectar SDA del
  SHT41 durante 3 ciclos y reconectarlo: durante la desconexión no llegan medidas, `err_sensor`
  sube en 3 (± 1) y, en el primer ciclo tras reconectar (≤ 61 s), llegan las tres medidas
  válidas, sin reinicio. El banco no tiene conmutador para SDA: la capacidad `sda-disconnect`
  del plan es «el operador desconecta el Dupont de SDA en la protoboard».
- **Acción.** Con el test en marcha, a los avisos del banco: desconectar el Dupont de SDA,
  esperar al segundo aviso (unos 3 min) y volver a conectarlo. Unos 5 minutos en total.
- **Estado.** Aplazada por el propietario el 2026-11-07 (opción 2): se hace cuando él esté
  frente al banco.

## 2026-11-07 · JRN-01.7 con la imagen nueva (acción física)

- **Contexto.** Aclaración de H-66 (plan H-68): la imagen de la rama `sntp` (cliente SNTP,
  comandos E13 y watchdog de 30 s) se fusiona a main después de la auditoría del propietario
  y de JRN-01.7 en verde con ella. JRN-01.7 necesita un corte manual: desenchufar el USB-C del
  lado de la placa y volver a enchufarlo a los avisos del banco.
- **Acción.** Con el propietario frente al banco: lanzar JRN-01.7 (y, si se quiere, TC-CFG-02 y
  TC-MQTT-04, 6 cortes en total como el 2026-11-07) con la imagen de la rama `sntp`.
- **Estado.** Pendiente; no se hace en el turno de noche.
