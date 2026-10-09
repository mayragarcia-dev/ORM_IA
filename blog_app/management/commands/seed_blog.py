from django.core.management.base import BaseCommand
from blog_app.models import Author, Article, Comment
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Seed the database with sample blog data'

    def handle(self, *args, **options):
        self.stdout.write('Seeding blog data...')

        # Clear existing data
        Comment.objects.all().delete()
        Article.objects.all().delete()
        Author.objects.all().delete()

        # Create authors
        authors_data = [
            {'name': 'Ana García', 'email': 'ana@example.com', 'bio': 'Escritora y desarrolladora'},
            {'name': 'Carlos López', 'email': 'carlos@example.com', 'bio': 'Experto en Python y Django'},
            {'name': 'María Rodríguez', 'email': 'maria@example.com', 'bio': 'Amante de la tecnología'},
            {'name': 'Juan Pérez', 'email': 'juan@example.com', 'bio': 'Blogger técnico'},
            {'name': 'Laura Martín', 'email': 'laura@example.com', 'bio': 'Ingeniera de software'},
        ]

        authors = []
        for data in authors_data:
            author = Author.objects.create(**data)
            authors.append(author)
            self.stdout.write(f'  Created author: {author.name}')

        # Create articles
        articles_data = [
            {
                'title': 'Introducción a Django ORM',
                'content': 'Django ORM es una herramienta poderosa para interactuar con la base de datos...',
                'author': authors[0],
                'is_published': True,
            },
            {
                'title': 'Consultas avanzadas con Django',
                'content': 'Aprende a hacer consultas complejas usando Q objects, annotate, aggregate...',
                'author': authors[1],
                'is_published': True,
            },
            {
                'title': 'Optimización de consultas en Django',
                'content': 'Cómo usar select_related, prefetch_related y only/defer para mejorar el rendimiento...',
                'author': authors[0],
                'is_published': True,
            },
            {
                'title': 'Migraciones en Django',
                'content': 'Todo lo que necesitas saber sobre el sistema de migraciones de Django...',
                'author': authors[2],
                'is_published': True,
            },
            {
                'title': 'Mejores prácticas con Django Models',
                'content': 'Patrones recomendados para definir modelos en Django...',
                'author': authors[3],
                'is_published': False,
            },
            {
                'title': 'Relaciones Many-to-Many en Django',
                'content': 'Cómo modelar relaciones muchos-a-muchos con through models...',
                'author': authors[1],
                'is_published': True,
            },
            {
                'title': 'Django Admin personalizado',
                'content': 'Personaliza el panel de administración de Django para tus modelos...',
                'author': authors[4],
                'is_published': True,
            },
            {
                'title': 'Testing en Django',
                'content': 'Escribe tests efectivos para tus modelos y vistas...',
                'author': authors[2],
                'is_published': True,
            },
        ]

        articles = []
        for data in articles_data:
            slug = slugify(data['title'])
            article = Article.objects.create(slug=slug, **data)
            articles.append(article)
            self.stdout.write(f'  Created article: {article.title}')

        # Create comments
        comments_data = [
            {'article': articles[0], 'author_name': 'Pedro', 'author_email': 'pedro@test.com', 'content': 'Muy buen artículo, gracias!'},
            {'article': articles[0], 'author_name': 'Lucía', 'author_email': 'lucia@test.com', 'content': 'Me ayudó mucho a entender el ORM.'},
            {'article': articles[1], 'author_name': 'Miguel', 'author_email': 'miguel@test.com', 'content': 'Los Q objects son muy útiles.'},
            {'article': articles[1], 'author_name': 'Sofia', 'author_email': 'sofia@test.com', 'content': '¿Hay ejemplos con Subquery?'},
            {'article': articles[2], 'author_name': 'Diego', 'author_email': 'diego@test.com', 'content': 'select_related vs prefetch_related, buena explicación.'},
            {'article': articles[3], 'author_name': 'Elena', 'author_email': 'elena@test.com', 'content': 'Las migraciones a veces dan problemas.'},
            {'article': articles[3], 'author_name': 'Roberto', 'author_email': 'roberto@test.com', 'content': 'Muy clara la explicación.'},
            {'article': articles[5], 'author_name': 'Patricia', 'author_email': 'patricia@test.com', 'content': 'El through model es clave.'},
            {'article': articles[5], 'author_name': 'Andrés', 'author_email': 'andres@test.com', 'content': 'Gracias por el ejemplo práctico.'},
            {'article': articles[6], 'author_name': 'Cristina', 'author_email': 'cristina@test.com', 'content': 'El admin de Django es muy potente.'},
            {'article': articles[7], 'author_name': 'Fernando', 'author_email': 'fernando@test.com', 'content': 'Testing es fundamental.'},
        ]

        for data in comments_data:
            comment = Comment.objects.create(**data)
            self.stdout.write(f'  Created comment: {comment}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully seeded: {Author.objects.count()} authors, '
                f'{Article.objects.count()} articles, {Comment.objects.count()} comments'
            )
        )