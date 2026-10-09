from django.core.management.base import BaseCommand
from blog.duel.team import pregunta_1, pregunta_2, pregunta_3, pregunta_4


class Command(BaseCommand):
    help = 'Run and verify ORM duel queries'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('=== DUEL: Verificando consultas ORM ===\n'))

        # Pregunta 1
        self.stdout.write(self.style.HTTP_INFO('Pregunta 1: Artículos publicados con autor y categoría'))
        qs1 = pregunta_1()
        self.stdout.write(f'  Query: {qs1.query}')
        self.stdout.write(f'  Resultados: {qs1.count()}')
        for art in qs1[:3]:
            cat = art.category.name if art.category else 'Sin categoría'
            self.stdout.write(f'    - {art.title} | Autor: {art.author.name} | Categoría: {cat}')
        self.stdout.write('')

        # Pregunta 2
        self.stdout.write(self.style.HTTP_INFO('Pregunta 2: Autores con artículos publicados y conteo'))
        qs2 = pregunta_2()
        self.stdout.write(f'  Query: {qs2.query}')
        self.stdout.write(f'  Resultados: {qs2.count()}')
        for author in qs2:
            self.stdout.write(f'    - {author.name}: {author.published_count} artículos')
        self.stdout.write('')

        # Pregunta 3
        self.stdout.write(self.style.HTTP_INFO('Pregunta 3: Artículos con etiquetas ORM/QuerySet y comentarios'))
        qs3 = pregunta_3()
        self.stdout.write(f'  Query: {qs3.query}')
        self.stdout.write(f'  Resultados: {qs3.count()}')
        for art in qs3:
            tags = ', '.join([t.name for t in art.tags.all()])
            comments = list(art.comments.all())
            self.stdout.write(f'    - {art.title} | Tags: {tags} | Comentarios: {len(comments)}')
        self.stdout.write('')

        # Pregunta 4
        self.stdout.write(self.style.HTTP_INFO('Pregunta 4: Categorías con 2+ artículos publicados'))
        qs4 = pregunta_4()
        self.stdout.write(f'  Query: {qs4.query}')
        self.stdout.write(f'  Resultados: {qs4.count()}')
        for cat in qs4:
            self.stdout.write(f'    - {cat.name}: {cat.published_articles_count} artículos')
        self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('=== Todas las consultas ejecutadas correctamente ==='))