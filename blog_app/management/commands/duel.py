from django.core.management.base import BaseCommand
from blog.duel.team import pregunta_1, pregunta_2, pregunta_3, pregunta_4, pregunta_5, pregunta_6, pregunta_7, pregunta_8


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

        # Pregunta 5
        self.stdout.write(self.style.HTTP_INFO('Pregunta 5: Artículos con n_comments y n_tags'))
        qs5 = pregunta_5()
        self.stdout.write(f'  Query: {qs5.query}')
        self.stdout.write(f'  Resultados: {qs5.count()}')
        for art in qs5:
            self.stdout.write(f'    - {art.title} | Comentarios: {art.n_comments} | Tags: {art.n_tags}')
        self.stdout.write('')

        # Pregunta 6
        self.stdout.write(self.style.HTTP_INFO('Pregunta 6: Autores con perfil'))
        qs6 = pregunta_6()
        self.stdout.write(f'  Query: {qs6.query}')
        self.stdout.write(f'  Resultados: {qs6.count()}')
        for author in qs6:
            profile = f" | Perfil: {author.profile.website}" if hasattr(author, 'profile') and author.profile else " | Sin perfil"
            self.stdout.write(f'    - {author.name}{profile}')
        self.stdout.write('')

        # Pregunta 7
        self.stdout.write(self.style.HTTP_INFO('Pregunta 7: 5 artículos recientes con todos los datos'))
        qs7 = pregunta_7()
        self.stdout.write(f'  Query: {qs7.query}')
        self.stdout.write(f'  Resultados: {qs7.count()}')
        for art in qs7:
            tags = ', '.join([t.name for t in art.tags.all()])
            comments = list(art.comments.all())
            profile = art.author.profile.website if hasattr(art.author, 'profile') and art.author.profile else 'Sin perfil'
            self.stdout.write(f'    - {art.title} | Autor: {art.author.name} ({profile}) | Cat: {art.category.name if art.category else "N/A"} | Tags: {tags} | Comentarios: {len(comments)}')
        self.stdout.write('')

        # Pregunta 8
        self.stdout.write(self.style.HTTP_INFO('Pregunta 8: Autores con artículos en categoría Django'))
        qs8 = pregunta_8()
        self.stdout.write(f'  Query: {qs8.query}')
        self.stdout.write(f'  Resultados: {qs8.count()}')
        for author in qs8:
            self.stdout.write(f'    - {author.name}: {author.django_articles_count} artículos en Django')
        self.stdout.write('')

        self.stdout.write(self.style.SUCCESS('=== Todas las 8 consultas ejecutadas correctamente ==='))