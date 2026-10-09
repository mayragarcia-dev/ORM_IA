# Entregable ORM + IA — Pasos 6 a 11

> Datos de referencia (fijos): 5 autores, 5 perfiles, 5 categorías, 9 etiquetas,
> 8 artículos (7 publicados) y 11 comentarios.

## Paso 6 — Veredicto de las respuestas de la IA

Comando: `python manage.py duel --source ai`

| Pregunta | Descripción | Veredicto (IA) | Consultas |
|----------|-------------|----------------|-----------|
| 1 | Artículos publicados con autor y categoría | Correcta (pero costosa) | 15 |
| 2 | Autores con artículos publicados y conteo | Correcta | 1 |
| 3 | Artículos con etiquetas ORM o QuerySet | Incorrecta | 1 |
| 4 | Categorías con 2+ artículos publicados | Incorrecta | 1 |
| 5 | Artículos con `n_comments` y `n_tags` | Incorrecta | 1 |
| 6 | Autores con perfil (1:1) | Correcta | 1 |
| 7 | 5 artículos recientes con datos precargados | Correcta (pero costosa) | 21 |
| 8 | Autores con artículos en categoría Django | ERROR | — |

**Resumen: 4/8 correctas.** (La fuente `team` da 8/8 correctas.)

## Paso 7 — Clasificación de los fallos de la IA

| Preg. | Clasificación | Evidencia |
|-------|---------------|------------|
| 1 | Correcta pero cara | El SQL no trae JOIN: `FROM blog_app_article WHERE is_published = True`. La versión del equipo usa `INNER JOIN author` + `LEFT OUTER JOIN category`. Duelo: 15 consultas vs 1. |
| 3 | Resultado distinto por el **significado** de la pregunta | Interpretó "ORM **o** QuerySet" como "ORM **y** QuerySet". SQL: `WHERE ("blog_app_tag"."slug" = orm AND "blog_app_tag"."slug" = queryset ...)` → ningún registro cumple ambas → 0 filas (esperado 3). |
| 4 | Resultado distinto por un **borde** | El `COUNT` no filtra publicados: `LEFT OUTER JOIN blog_app_article ... HAVING COUNT(...) >= 2`. Incluye "Python"(2) contando el artículo no publicado. Esperado: solo `[('Django', 4)]`; obtenido: `[('Django', 4), ('Python', 2)]`. |
| 5 | **Conteos multiplicados** | Dos `LEFT OUTER JOIN` (comentarios y etiquetas) en la misma query anotada → producto cartesiano. "Consultas avanzadas": 2 comentarios × 3 tags = 6 en ambos campos. Esperado `(2, 3)`, obtenido `(6, 6)`. |
| 7 | Correcta pero cara | Resultado correcto pero sin `select_related`/`prefetch_related`. Duelo: 21 consultas vs 3. |
| 8 | **Campo inventado** | `FieldError: Unsupported lookup 'published' for ManyToOneRel`. Se usó `articles__published` en lugar de `articles__is_published`. |

Fallos por categoría: significado (1), borde (1), conteos multiplicados (1),
campo inventado (1), correcta pero cara (2). Correctas: preguntas 2 y 6.

## Paso 8 — IA desde cero (pegar `blog/models.py`)

Comando: `python manage.py duel --source assistant`

Se le pidió al asistente de IA las ocho consultas **desde cero**, pasándole el
contenido de `blog/models.py`. Las respuestas quedan en `blog/duel/assistant.py`.
Resultado: **8/8 correctas**.

| Preg. | Fuente `ai` (paso 6) | Fuente `assistant` (paso 8) | ¿Reincide el fallo? |
|-------|----------------------|-----------------------------|---------------------|
| 1 | Correcta pero costosa (15) | Correcta (1) | No — usa `select_related` |
| 2 | Correcta | Correcta | No |
| 3 | Incorrecta (significado) | Correcta | No — usa `Q(orm) OR Q(queryset)` |
| 4 | Incorrecta (borde) | Correcta | No — filtra `is_published` en el `Count` |
| 5 | Incorrecta (conteos multiplicados) | Correcta | No — usa `Subquery`/`OuterRef` |
| 6 | Correcta | Correcta | No |
| 7 | Correcta pero costosa (21) | Correcta (3) | No — `select_related` + `prefetch_related` |
| 8 | ERROR (campo inventado) | Correcta | No — usa `articles__is_published` |

**Conclusión:** el asistente, al partir de `blog/models.py`, no reincide en
ninguno de los cinco tipos de fallo del paso 6: significado (Q3), borde (Q4),
conteos multiplicados (Q5), campo inventado (Q8) y coste (Q1/Q7).

## Paso 9 — Prueba que falla (23 consultas vs 2 esperadas)

Comando: `python manage.py test blog.tests.test_front_page -v 2`

```
FAIL: test_front_page_usa_dos_consultas
blog.tests.test_front_page.FrontPageQueryCountTest.test_front_page_usa_dos_consultas
----------------------------------------------------------------------
Traceback (most recent call last):
  File "blog/tests/test_front_page.py", line 36, in test_front_page_usa_dos_consultas
    with self.assertNumQueries(2):
AssertionError: 23 != 2 : 23 queries executed, 2 expected
Captured queries were:
 1. SELECT COUNT(*) AS "__count" FROM "blog_app_article" WHERE "is_published" = 1
 2. SELECT ... FROM "blog_app_article" WHERE "is_published" = 1 ORDER BY "published_at" DESC
 3. SELECT ... FROM "blog_app_author" WHERE "id" = 2
 4. SELECT ... FROM "blog_app_category" WHERE "id" = 2
 5. SELECT ... FROM "blog_app_tag" INNER JOIN "blog_app_article_tags" WHERE "article_id" = 6
 6. SELECT ... FROM "blog_app_author" WHERE "id" = 5
 7. SELECT ... FROM "blog_app_category" WHERE "id" = 1
 8. SELECT ... FROM "blog_app_tag" ... WHERE "article_id" = 7
 ... (se repite el patrón autor/categoría/etiquetas para los 7 artículos publicados)
23. SELECT ... FROM "blog_app_tag" ... WHERE "article_id" = 1
----------------------------------------------------------------------
Ran 1 test in 0.039s
FAILED (failures=1)
```

## Paso 10 — ¿De dónde salen las 23 consultas?

`front_page_context()` sin optimizar produce consultas por cada acceso a una
relación de cada artículo:

| Origen | Consultas |
|--------|-----------|
| `COUNT(*)` del total publicados | 1 |
| `SELECT` de los 7 artículos publicados | 1 |
| Autor de cada artículo (`article.author`) | 7 |
| Categoría de cada artículo (`article.category`) | 7 |
| Etiquetas de cada artículo (`article.tags.all()`) | 7 |
| **Total** | **23** |

Es un caso clásico **N+1**: 1 consulta para la lista + 3 consultas por artículo
(autor, categoría, etiquetas). Con `N` artículos publicados el total crece como
`3N + 2`, por lo que cada artículo nuevo en la portada agrega 3 consultas.

## Paso 11 — Optimización de `blog/queries.py`

- **Antes:** 23 consultas (test falla).
- **Después:** 2 consultas (test pasa).

Cambio aplicado:

```python
articles = list(
    Article.objects.filter(is_published=True)
    .select_related('author', 'category')   # FK en el mismo SELECT (JOIN)
    .prefetch_related('tags')               # M2M en 1 consulta extra
    .order_by('-published_at')
)
return {'articles': articles, 'total': len(articles)}   # total sin COUNT extra
```

- `select_related('author', 'category')`: 1 sola consulta con JOIN para las FK.
- `prefetch_related('tags')`: 1 consulta adicional para todas las etiquetas.
- `len(articles)` sobre la lista ya evaluada: evita la consulta `COUNT`.

Resultado de la suite completa (`python manage.py test`): ver más abajo.

## Paso 15 (borrador) — Tabla de uso de IA

| Qué se le pidió | Qué respondió | Aceptado / Rechazado | Por qué |
|-----------------|---------------|----------------------|---------|
| Respuestas a las 8 preguntas del duelo | `blog/duel/ai.py` (4/8 correctas) | Rechazadas las incorrectas | Fallos de borde, significado, conteos multiplicados y campo inventado |
| Optimizar la portada | `select_related` + `prefetch_related` | Aceptado tras verificarlo con el test (23→2) | Coincide con el comportamiento medido |
