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


def pregunta_5():
    """
    Obtener todos los artículos publicados anotados con el número de comentarios
    aprobados (n_comments) y el número de etiquetas (n_tags),
    ordenados por número de comentarios descendente.
    Usa subconsultas para evitar el producto cartesiano.
    """
    from django.db.models import Subquery, OuterRef, Count, IntegerField

    comments_subquery = Comment.objects.filter(
        article=OuterRef('pk'),
        is_approved=True
    ).values('article').annotate(
        count=Count('id')
    ).values('count')

    tags_subquery = Article.tags.through.objects.filter(
        article=OuterRef('pk')
    ).values('article').annotate(
        count=Count('id')
    ).values('count')

    return Article.objects.filter(
        is_published=True
    ).annotate(
        n_comments=Subquery(comments_subquery, output_field=IntegerField()),
        n_tags=Subquery(tags_subquery, output_field=IntegerField())
    ).order_by('-n_comments')


def pregunta_6():
    """
    Obtener todos los autores con su perfil (si existe),
    ordenados por nombre.
    """
    return Author.objects.select_related('profile').order_by('name')


def pregunta_7():
    """
    Obtener los 5 artículos más recientes publicados con todos sus datos relacionados
    precargados eficientemente: autor, perfil del autor, categoría, etiquetas
    y comentarios aprobados.
    """
    return Article.objects.filter(
        is_published=True
    ).select_related(
        'author', 'author__profile', 'category'
    ).prefetch_related(
        'tags',
        Prefetch('comments', queryset=Comment.objects.filter(is_approved=True))
    ).order_by('-published_at')[:5]


def pregunta_8():
    """
    Obtener los autores que han publicado artículos en la categoría 'Django',
    con el conteo de sus artículos en esa categoría,
    ordenados por conteo descendente.
    """
    return Author.objects.filter(
        articles__category__slug='django',
        articles__is_published=True
    ).annotate(
        django_articles_count=Count('articles', filter=Q(articles__category__slug='django', articles__is_published=True))
    ).distinct().order_by('-django_articles_count')