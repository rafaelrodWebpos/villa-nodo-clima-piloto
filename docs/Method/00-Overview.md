# Nodo Clima Piloto — Method (CÓMO)

El **contrato de build**: las reglas de cómo se construye y se cambia este
proyecto. Punto de entrada de cualquier tarea:
**[`AI-Workflow.md`](AI-Workflow.md)**.

| Ruta | Contenido |
|------|-----------|
| `AI-Workflow.md` | El ciclo que sigue todo cambio. Léelo antes de tocar código. |
| `standards/` | Reglas portables, reutilizables en cualquier proyecto: ingeniería y pruebas. |
| `project/` | Lo propio de este proyecto: capas, estructura de fuentes, dependencias de ESP-IDF, prohibiciones y reglas del repositorio público. |

Una regla pertenece aquí cuando restringe **cómo se escribe, se estructura o se
verifica** el código sin ser observable desde fuera del sistema en marcha. Si un
tester de caja negra pudiera verificarla, es un requisito y va en el FSD.

El mapa de planos, el orden de autoridad y la regla de reparto están en
[`../00-Overview.md`](../00-Overview.md).
