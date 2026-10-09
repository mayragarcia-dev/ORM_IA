from blog_app.models import Author, AuthorProfile, Category, Tag, Article, Comment
from django.db.models import Count, Q, Prefetch
from django.utils import timezone
from datetime import timedelta


def pregunta_1():
    """
    Obtener todos los artículos publicados con su autor y categoría,
    ordenados por fecha de publicación descendente.
    """
    return Article.objects.filter(
        is_published=True
    ).select_related(
        'author', 'category'
    ).order_by('-published_at')


def pregunta_2():
    """
    Obtener todos los autores que tienen al menos un artículo publicado,
    junto con el conteo de sus artículos publicados.
    """
    return Author.objects.filter(
        articles__is_published=True
    ).annotate(
        published_count=Count('articles', filter=Q(articles__is_published=True))
    ).distinct().order_by('-published_count')


def pregunta_3():
    """
    Obtener todos los artículos que tienen la etiqueta 'ORM' o 'QuerySet',
    con sus etiquetas y comentarios aprobados precargados.
    """
    return Article.objects.filter(
        tags__slug__in=['orm', 'queryset'],
        is_published=True
    ).prefetch_related(
        'tags',
        Prefetch('comments', queryset=Comment.objects.filter(is_approved=True))
    ).distinct().order_by('-published_at')


def pregunta_4():
    """
    Obtener las categorías con el número de artículos publicados en cada una,
    solo para categorías que tengan al menos 2 artículos publicados.
    """
    return Category.objects.annotate(
        published_articles_count=Count('articles', filter=Q(articles__is_published=True))
    ).filter(
        published_articles_count__gte=2
    ).order_by('-published_articles_count')