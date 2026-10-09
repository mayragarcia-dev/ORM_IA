from blog_app.models import Article


def front_page_context():
    """
    Contexto de la portada del blog.

    Devuelve los artículos publicados ordenados por fecha y el total de
    artículos publicados. La plantilla recorre cada artículo y muestra su
    autor, su categoría y sus etiquetas.

    Optimización:
      - select_related('author', 'category') resuelve las FK (autor y
        categoría) en la MISMA consulta de artículos (JOIN).
      - prefetch_related('tags') trae todas las etiquetas en UNA consulta
        adicional (relación M2M).
      - El total se obtiene con len() sobre la lista ya evaluada, sin
        disparar una consulta COUNT extra.
    """
    articles = list(
        Article.objects.filter(is_published=True)
        .select_related('author', 'category')
        .prefetch_related('tags')
        .order_by('-published_at')
    )
    return {'articles': articles, 'total': len(articles)}
