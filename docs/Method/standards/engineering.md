# Estándar — Convenciones de ingeniería (portable)

- **Reutilizar antes de añadir.** Busca un helper, módulo o skill existente
  antes de escribir código nuevo.
- **El cambio más pequeño que cumpla la regla.** Sin alcance especulativo ni
  refactors mezclados con un arreglo.
- **Un módulo por componente.** Nunca se pliega una interfaz dentro de su único
  consumidor.
- **Las dependencias apuntan en un solo sentido.** Las capas inferiores no
  importan a las superiores; si la necesidad parece invertirse, se invierte en
  la raíz de composición con un callback o un registro.
- **Extraer núcleos puros.** La decisión se separa de la E/S: un parser, una
  conversión, una transición de estado o una validación es una función libre,
  sin hardware, red ni sistema de ficheros, para que la alcance el nivel host.
- **Verificar antes del commit.** El build, el lint y los tests del proyecto
  pasan (comandos en `../project/arquitectura.md`).
- **Los errores fallan de forma visible.** Mensajes accionables, ningún `catch`
  silencioso, ningún código de retorno ignorado.
- **Los secretos nunca están en el código ni en la documentación.** Solo se
  documenta *dónde* residen. Se valida toda entrada externa.
- **Commits.** Mensaje en imperativo, con una línea de resumen de 72
  caracteres o menos y el motivo en el cuerpo. Nunca se commitean salidas
  generadas, artefactos de build ni secretos.
