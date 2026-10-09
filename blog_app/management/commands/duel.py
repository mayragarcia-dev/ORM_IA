"""
Comando de duelo ORM.

Ejecuta las 8 preguntas de una fuente (`team` o `ai`), las compara contra la
respuesta esperada (calculada de forma independiente) y reporta, por pregunta:

  - el SQL de la consulta principal,
  - el número de consultas SQL ejecutadas,
  - el veredicto (correcta / incorrecta / error),
  - la diferencia con lo esperado cuando falla,
  - la marca "correcta pero cara" cuando el resultado es correcto pero usa
    más consultas que la versión de referencia del equipo.

Uso:
    python manage.py duel                     # fuente team (por defecto)
    python manage.py duel --source ai         # respuestas del asistente de IA (paso 6)
    python manage.py duel --source assistant  # respuestas correctas desde cero (paso 8)
    python manage.py duel --sql               # imprime el SQL de cada respuesta
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.test.utils import CaptureQueriesContext

from blog_app.models import Article, Author, AuthorProfile, Category


def _get_module(source):
    if source == 'ai':
        from blog.duel import ai
        return ai
    if source == 'assistant':
        from blog.duel import assistant
        return assistant
    from blog.duel import team
    return team


def _expected(n):
    """Respuesta correcta, calculada de forma directa e independiente."""
    if n == 1:
        return sorted(
            (a.title, a.author.name, a.category.name if a.category_id else None)
            for a in Article.objects.filter(is_published=True)
            .select_related('author', 'category')
        )
    if n == 2:
        rows = []
        for author in Author.objects.all():
            count = sum(1 for art in author.articles.all() if art.is_published)
            if count:
                rows.append((author.name, count))
        return sorted(rows)
    if n == 3:
        rows = []
        for art in Article.objects.filter(is_published=True).prefetch_related('tags'):
            slugs = {t.slug for t in art.tags.all()}
            if slugs & {'orm', 'queryset'}:
                n_comments = art.comments.filter(is_approved=True).count()
                rows.append((art.title, tuple(sorted(t.name for t in art.tags.all())), n_comments))
        return sorted(rows)
    if n == 4:
        rows = []
        for cat in Category.objects.all():
            count = sum(1 for art in cat.articles.all() if art.is_published)
            if count >= 2:
                rows.append((cat.name, count))
        return sorted(rows)
    if n == 5:
        rows = []
        for art in Article.objects.filter(is_published=True):
            rows.append((art.title, art.comments.filter(is_approved=True).count(), art.tags.count()))
        return sorted(rows)
    if n == 6:
        rows = []
        for author in Author.objects.all():
            rows.append((author.name, AuthorProfile.objects.filter(author=author).exists()))
        return sorted(rows)
    if n == 7:
        rows = []
        for art in (
            Article.objects.filter(is_published=True)
            .select_related('author', 'category')
            .prefetch_related('tags')
            .order_by('-published_at')[:5]
        ):
            rows.append((
                art.title,
                art.author.name,
                art.category.name if art.category_id else None,
                tuple(sorted(t.name for t in art.tags.all())),
                art.comments.filter(is_approved=True).count(),
            ))
        return rows
    if n == 8:
        rows = []
        for author in Author.objects.all():
            count = sum(
                1 for art in author.articles.all()
                if art.is_published and art.category_id and art.category.slug == 'django'
            )
            if count:
                rows.append((author.name, count))
        return sorted(rows)
    raise ValueError(n)


def _normalize(n, result):
    """Convierte el resultado de una pregunta a una estructura comparable."""
    if n == 1:
        return sorted(
            (a.title, a.author.name, a.category.name if a.category_id else None)
            for a in result
        )
    if n == 2:
        return sorted((a.name, a.published_count) for a in result)
    if n == 3:
        return sorted(
            (a.title, tuple(sorted(t.name for t in a.tags.all())), len(list(a.comments.all())))
            for a in result
        )
    if n == 4:
        return sorted((c.name, c.published_articles_count) for c in result)
    if n == 5:
        return sorted((a.title, a.n_comments, a.n_tags) for a in result)
    if n == 6:
        rows = []
        for author in result:
            try:
                has_profile = author.profile is not None
            except Exception:
                has_profile = False
            rows.append((author.name, has_profile))
        return sorted(rows)
    if n == 7:
        return [
            (
                a.title,
                a.author.name,
                a.category.name if a.category_id else None,
                tuple(sorted(t.name for t in a.tags.all())),
                len(list(a.comments.all())),
            )
            for a in result
        ]
    if n == 8:
        return sorted((a.name, a.django_articles_count) for a in result)
    raise ValueError(n)


def _run(module, n):
    """Ejecuta la pregunta n capturando consultas y normalizando el resultado."""
    try:
        with CaptureQueriesContext(connection) as ctx:
            result = getattr(module, 'pregunta_%d' % n)()
            normalized = _normalize(n, result)
        sql = ctx.captured_queries[0]['sql'] if ctx.captured_queries else '(sin consultas)'
        return {
            'normalized': normalized,
            'count': len(ctx.captured_queries),
            'sql': sql,
            'error': None,
        }
    except Exception as exc:
        return {'normalized': None, 'count': None, 'sql': None, 'error': exc}


def _diff(expected, obtained):
    """Primeras diferencias simétricas entre dos colecciones (con orden)."""
    out = []
    if isinstance(expected, list) and isinstance(obtained, list):
        for i in range(max(len(expected), len(obtained))):
            e = expected[i] if i < len(expected) else '<faltante>'
            o = obtained[i] if i < len(obtained) else '<de más>'
            if e != o:
                out.append((i, e, o))
            if len(out) >= 5:
                break
    return out


class Command(BaseCommand):
    help = 'Ejecuta y verifica las 8 consultas del duelo ORM.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source', choices=['team', 'ai', 'assistant'], default='team',
            help='Fuente de las respuestas (team, ai o assistant).',
        )
        parser.add_argument(
            '--sql', action='store_true',
            help='Imprime el SQL de la consulta principal de cada pregunta.',
        )

    def handle(self, *args, **options):
        source = options['source']
        module = _get_module(source)
        show_sql = options['sql']

        self.stdout.write(self.style.NOTICE(f'=== DUEL ORM :: fuente = {source} ===\n'))

        expected = {n: _expected(n) for n in range(1, 9)}

        reference_counts = {}
        for n in range(1, 9):
            reference_counts[n] = _run(_get_module('team'), n)['count']

        resultados = []
        for n in range(1, 9):
            run = _run(module, n)
            self.stdout.write(self.style.HTTP_INFO(f'--- Pregunta {n} ---'))

            if run['error'] is not None:
                err = run['error']
                self.stdout.write(self.style.ERROR(
                    f'  Veredicto: ERROR ({type(err).__name__}: {err})'
                ))
                self.stdout.write('  Clasificacion probable: campo inventado / consulta invalida\n')
                resultados.append((n, 'ERROR', None, str(err)))
                continue

            self.stdout.write(f'  Consultas SQL: {run["count"]}')
            if show_sql:
                self.stdout.write(f'  SQL: {run["sql"]}')

            if run['normalized'] == expected[n]:
                if source != 'team' and run['count'] > reference_counts[n]:
                    veredicto = 'CORRECTA (pero costosa)'
                    self.stdout.write(self.style.WARNING(
                        f'  Veredicto: {veredicto} '
                        f'({run["count"]} consultas vs {reference_counts[n]} de la referencia)'
                    ))
                else:
                    veredicto = 'CORRECTA'
                    self.stdout.write(self.style.SUCCESS(f'  Veredicto: {veredicto}'))
                resultados.append((n, veredicto, run['count'], None))
            else:
                veredicto = 'INCORRECTA'
                self.stdout.write(self.style.ERROR(f'  Veredicto: {veredicto}'))
                self.stdout.write(f'  Esperado ({len(expected[n])}): {expected[n][:5]}')
                self.stdout.write(f'  Obtenido ({len(run["normalized"])}): {run["normalized"][:5]}')
                for i, e, o in _diff(expected[n], run['normalized']):
                    self.stdout.write(f'    pos {i}: esperado={e!r}  obtenido={o!r}')
                resultados.append((n, veredicto, run['count'], _diff(expected[n], run['normalized'])))
            self.stdout.write('')

        correctas = sum(1 for _, v, _, _ in resultados if v.startswith('CORRECTA'))
        self.stdout.write(self.style.NOTICE(
            f'=== Resumen fuente={source}: {correctas}/8 correctas ==='
        ))
