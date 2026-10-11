# Nodo Clima Piloto — Documentación

Tres planos, tres preguntas, tres lectores. Cada frase pertenece exactamente a
uno de ellos.

| Plano | Pregunta | Directorio | Lector |
|---|---|---|---|
| **QUÉ** | ¿Qué debe ser cierto del sistema? | [`Functionality/`](Functionality/) | Quien juzga si es correcto: revisor, tester, mantenedor futuro |
| **CÓMO** | ¿Cómo se construye y se cambia? | [`Method/`](Method/) | Quien escribe el próximo cambio, persona o agente |
| **OPERAR** | ¿Cómo se instala y se usa? | [`UserDocumentation/`](UserDocumentation/) | Quien instala, maneja o recupera el sistema en marcha |

**Orden de autoridad: el FSD define el objetivo y el Method define el camino.**
Si chocan, el FSD manda sobre *qué debe ser cierto* y el Method sobre *cómo
llegar*. El manual describe el sistema tal como está construido: si contradice
a cualquiera de los dos, está desactualizado, porque se movió la realidad o la
especificación.

Ninguno de los tres guarda historia ni narra justificaciones. Eso vive en
`git log`.

## Por dónde empezar

| Si estás… | Lee |
|---|---|
| Haciendo un cambio | [`Method/AI-Workflow.md`](Method/AI-Workflow.md): el ciclo que sigue todo cambio |
| Juzgando la corrección | [`Functionality/FSD-nodo-clima.md`](Functionality/FSD-nodo-clima.md): requisitos, máquina de estados, contratos de verificación |
| Instalando u operando | [`UserDocumentation/Manual-de-usuario.md`](UserDocumentation/Manual-de-usuario.md) |
| Preguntándote por qué | `git log`: una decisión deja su efecto en un plano y su motivo en el commit |

## Dónde va una frase nueva

Pregunta en este orden; gana el primer «sí»:

1. Es observable desde fuera y debe cumplirse → **Functionality**
2. Restringe cómo se escribe o se verifica el código → **Method**
3. Le dice a una persona cómo operar o recuperar el sistema → **UserDocumentation**
4. Trata de cómo colaborar con un asistente IA → `CLAUDE.md`, que no es un plano
5. Explica por qué se tomó una decisión pasada → el mensaje de commit

Dos preguntas resuelven los casos difíciles. *¿Podría verificarlo un tester de
caja negra?* Si la respuesta es sí, es QUÉ. *¿Sobreviviría a una reescritura en
otro lenguaje?* Si la respuesta es no, es CÓMO.

## No hay fichero de decisiones

Una decisión tomada deja su **efecto** como contenido en presente en el plano
que gobierna, y su motivo en el mensaje de commit. Un «no se debe» con peso
real se convierte en un requisito negativo explícito.

## Reglas de redacción

**En presente.** Se escribe lo que es cierto ahora. Se eliminan en cuanto
aparecen expresiones como «ahora usa», «antes», «desde la v2» o «decidimos».
La única excepción es el bloque de metadatos del FSD.

**Un solo hogar por hecho.** Cada hecho se escribe una vez y los demás sitios
enlazan a él.

**Repositorio público.** Ningún plano contiene credenciales, SSIDs, direcciones
de la instalación, nombres de zona reales ni datos que identifiquen el lugar
(FSD NFR-SEC-01). Los ejemplos usan `zona1` y `clima-a1b2c3`.
