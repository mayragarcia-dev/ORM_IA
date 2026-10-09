"""
Respuestas del asistente de IA (paso 8) generadas desde cero a partir del
contenido de `blog_app/models.py`.

A diferencia de `blog/duel/ai.py`, estas consultas son las correctas y
optimizadas: usan `select_related` para FK/1:1, `prefetch_related` para M2M y
reversas, y `Subquery` para evitar productos cartesianos en los conteos.

Se ejecutan con:  python manage.py duel --source assistant
"""

from blog_app.models import Article, Author, Category, Comment
from django.db.models import Count, Q, Subquery, OuterRef, IntegerField, Prefetch


def pregunta_1():
    """Artículos publicados con autor y categoría, orden por fecha desc."""
    return Article.objects.filter(
        is_published=True
    ).select_related(
        'author', 'category'
    ).order_by('-published_at')


def pregunta_2():
    """Autores con al menos un artículo publicado y su conteo."""
    return Author.objects.filter(
        articles__is_published=True
    ).annotate(
        published_count=Count('articles', filter=Q(articles__is_published=True))
    ).distinct().order_by('-published_count')


def pregunta_3():
    """Artículos con la etiqueta ORM o QuerySet, con tags y comentarios aprobados."""
    return Article.objects.filter(
        Q(tags__slug='orm') | Q(tags__slug='queryset'),
        is_published=True,
    ).prefetch_related(
        'tags',
        Prefetch('comments', queryset=Comment.objects.filter(is_approved=True)),
    ).distinct().order_by('-published_at')


def pregunta_4():
    """Categorías con al menos 2 artículos publicados y su conteo."""
    return Category.objects.annotate(
        published_articles_count=Count('articles', filter=Q(articles__is_published=True))
    ).filter(
        published_articles_count__gte=2
    ).order_by('-published_articles_count')


def pregunta_5():
    """Artículos publicados con n_comments y n_tags (subconsultas, sin cruce)."""
    comments_subquery = Comment.objects.filter(
        article=OuterRef('pk'), is_approved=True
    ).values('article').annotate(c=Count('id')).values('c')

    tags_subquery = Article.tags.through.objects.filter(
        article=OuterRef('pk')
    ).values('article').annotate(c=Count('id')).values('c')

    return Article.objects.filter(
        is_published=True
    ).annotate(
        n_comments=Subquery(comments_subquery, output_field=IntegerField()),
        n_tags=Subquery(tags_subquery, output_field=IntegerField()),
    ).order_by('-n_comments')


def pregunta_6():
    """Autores con su perfil (si existe), ordenados por nombre."""
    return Author.objects.select_related('profile').order_by('name')


def pregunta_7():
    """5 artículos publicados más recientes con todos los datos precargados."""
    return Article.objects.filter(
        is_published=True
    ).select_related(
        'author', 'author__profile', 'category'
    ).prefetch_related(
        'tags',
        Prefetch('comments', queryset=Comment.objects.filter(is_approved=True)),
    ).order_by('-published_at')[:5]


def pregunta_8():
    """Autores con artículos publicados en la categoría Django y su conteo."""
    return Author.objects.filter(
        articles__category__slug='django',
        articles__is_published=True,
    ).annotate(
        django_articles_count=Count(
            'articles',
            filter=Q(articles__category__slug='django', articles__is_published=True),
        )
    ).distinct().order_by('-django_articles_count')
