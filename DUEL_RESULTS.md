# Resultados del Duelo ORM

## Resumen de intentos por pregunta

| Pregunta | Descripción | Intentos | Estado |
|----------|-------------|----------|--------|
| 1 | Artículos publicados con autor y categoría | 1 | ✅ Correcta |
| 2 | Autores con artículos publicados y conteo | 1 | ✅ Correcta |
| 3 | Artículos con etiquetas ORM/QuerySet y comentarios | 1 | ✅ Correcta |
| 4 | Categorías con 2+ artículos publicados | 1 | ✅ Correcta |
| 5 | Artículos con n_comments y n_tags (anotados) | 2 | ✅ Correcta |
| 6 | Autores con perfil (1:1) | 1 | ✅ Correcta |
| 7 | 5 artículos recientes con todos los datos precargados | 1 | ✅ Correcta |
| 8 | Autores con artículos en categoría Django | 1 | ✅ Correcta |

## Detalle de la Pregunta 5

**Intento 1:** Usé `Count()` con `filter` para ambas anotaciones en una sola query.
- **Problema:** Producto cartesiano - los conteos se multiplicaban (ej: 2 comentarios × 3 tags = 6 para cada uno)
- **Resultado incorrecto:** "Consultas avanzadas con Django" mostraba 6 comentarios y 6 tags (real: 2 comentarios, 3 tags)

**Intento 2:** Usé `Subquery` con `OuterRef` para conteos independientes.
- **Solución:** Subconsultas separadas para comentarios y tags evitan el producto cartesiano
- **Resultado correcto:** Conteos precisos para cada artículo

## Consultas finales en `blog/duel/team.py`

Todas las 8 funciones devuelven `QuerySet` optimizados usando:
- `select_related()` para ForeignKey y OneToOne
- `prefetch_related()` + `Prefetch()` para ManyToMany y reverse ForeignKey
- `annotate()` + `Count()` con `filter` para agregaciones condicionales
- `Subquery()` + `OuterRef()` para evitar productos cartesianos
- `distinct()` cuando hay joins que duplican filas