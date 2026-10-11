# Nodo Clima Piloto — Flujo de trabajo con IA (el contrato de build)

Léelo antes de cualquier cambio. Así se construye la funcionalidad nueva y así
se mantiene la documentación sincronizada con ella.

## El ciclo

**1. Localiza el contrato.** Busca la regla del FSD a la que sirve el trabajo en
`docs/Functionality/FSD-nodo-clima.md`. Si no existe, el trabajo empieza por
definir el **QUÉ** (`/define update`): un requisito nuevo, atómico y falsable,
no código. Un cambio sin regla detrás es alcance no pedido o un requisito no
documentado, y hay que resolver ambos casos antes de implementar.

**2. Construye según el Method.** Sigue `standards/` y `project/`. Reutiliza un
módulo, helper o skill existente antes de añadir código. Haz el cambio más
pequeño que cumpla la regla, sin alcance especulativo ni refactors de paso.

**3. Prueba: es la puerta, no un añadido.** Un cambio **no está terminado**
hasta que su test existe y pasa. Según `standards/testing.md`: declara la
prueba en `testing/test-plan.yaml`, escribe el test junto al código y deja la
suite en verde. Un arreglo de bug empieza por su **test de regresión**, que
debe fallar antes del arreglo y pasar después.

**4. Reconcilia la documentación.**
- El **FSD** absorbe el comportamiento nuevo o cambiado. Verifica, no
  transcribas: si el código se desvía de la especificación, se arregla el
  código.
- El **manual** absorbe todo lo que notaría quien opera el nodo.
- El **Method** no cambia salvo que el cambio enseñe una regla que sea cierta
  para todo el proyecto.
- Todo en presente.

**5. Verifica en ambos sentidos.** La implementación cumple el FSD, y ninguna
regla del FSD queda sin implementar en silencio.

## Puerta de calidad de un requisito

Antes de entrar en el FSD, un requisito debe ser:

- **Atómico**: una sola obligación.
- **Falsable**: precondición, estímulo, respuesta observable, plazo,
  tolerancia, comportamiento ante fallo y nivel de prueba.
- **Libre de palabras vagas**: *adecuado, elegante, amigable, razonable,
  suficiente, robusto, transparente, aceptable, funcionamiento normal, mejor
  esfuerzo*.
- **Con procedencia**: `[user]`, `[derived]`, `[code]` o `[pack:<dominio>]`.

## Roles

- El propietario del repositorio aprueba los cambios del FSD y acepta o rechaza
  los valores `(propuesto)`.
- `/define` escribe el FSD; `/build` es dueño del plan de pruebas y del orden
  de trabajo; los skills de desarrollo escriben el código y los tests.
- Una contradicción entre planos la arbitra el propietario; mientras tanto,
  manda el FSD.
