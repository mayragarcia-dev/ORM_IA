import io

from django.core.management import call_command
from django.test import TestCase

from blog.queries import front_page_context


class FrontPageQueryCountTest(TestCase):
    """
    La portada del blog debe renderizarse con un número constante de consultas.

    Se esperan 2 consultas:
      1. artículos publicados (con autor y categoría via select_related)
      2. etiquetas de esos artículos (prefetch_related)

    Con la implementación sin optimizar (N+1) se disparan 23 consultas.
    """

    @classmethod
    def setUpTestData(cls):
        call_command('seed_blog', verbosity=0, stdout=io.StringIO())

    def render_front_page(self):
        context = front_page_context()
        total = context['total']
        rendered = []
        for article in context['articles']:
            rendered.append({
                'title': article.title,
                'author': article.author.name,
                'category': article.category.name if article.category else None,
                'tags': [tag.name for tag in article.tags.all()],
            })
        return total, rendered

    def test_front_page_usa_dos_consultas(self):
        with self.assertNumQueries(2):
            total, rendered = self.render_front_page()

        self.assertEqual(total, 7)
        self.assertEqual(len(rendered), 7)
