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
