"""
Respuestas generadas por un asistente de IA para el duelo ORM.

Este módulo se usa con `python manage.py duel --source ai` y NO debe
considerarse una plantilla de referencia: varias respuestas son incorrectas
a propósito/de forma natural y el duelo las marca como tales junto con su
clasificación.

Mapeo de fallos presente en estas respuestas:
  - pregunta_1: correcta pero cara (sin select_related).
  - pregunta_2: correcta.
  - pregunta_3: resultado distinto por el significado de la pregunta
                (interpreta "ORM o QuerySet" como "ORM y QuerySet").
  - pregunta_4: resultado distinto por un borde (cuenta también artículos
                no publicados).
  - pregunta_5: conteos multiplicados (producto cartesiano de dos Count()).
  - pregunta_6: correcta.
  - pregunta_7: correcta pero cara (sin select_related ni prefetch).
  - pregunta_8: campo inventado (`articles__published`).
"""

from blog_app.models import Article, Author, Category, Comment
from django.db.models import Count, Q


def pregunta_1():
    """Artículos publicados con autor y categoría, orden por fecha desc."""
    return Article.objects.filter(is_published=True).order_by('-published_at')


def pregunta_2():
    """Autores con al menos un artículo publicado y su conteo."""
    return Author.objects.filter(
        articles__is_published=True
    ).annotate(
        published_count=Count('articles', filter=Q(articles__is_published=True))
    ).distinct()


def pregunta_3():
    """Artículos con la etiqueta ORM o QuerySet (lee "o" como "y")."""
    return Article.objects.filter(
        Q(tags__slug='orm') & Q(tags__slug='queryset'),
        is_published=True,
    ).prefetch_related('tags', 'comments').distinct()


def pregunta_4():
    """Categorías con al menos 2 artículos (cuenta también no publicados)."""
    return Category.objects.annotate(
        published_articles_count=Count('articles')
    ).filter(published_articles_count__gte=2)


def pregunta_5():
    """Artículos publicados con n_comments y n_tags (conteos cruzados)."""
    return Article.objects.filter(is_published=True).annotate(
        n_comments=Count('comments'),
        n_tags=Count('tags'),
    )


def pregunta_6():
    """Autores con su perfil, ordenados por nombre."""
    return Author.objects.select_related('profile').order_by('name')


def pregunta_7():
    """Los 5 artículos publicados más recientes con datos relacionados."""
    return Article.objects.filter(is_published=True).order_by('-published_at')[:5]


def pregunta_8():
    """Autores con artículos en la categoría Django (campo `published`)."""
    return Author.objects.filter(
        articles__category__slug='django',
        articles__published=True,
    ).annotate(
        django_articles_count=Count('articles')
    ).distinct()
