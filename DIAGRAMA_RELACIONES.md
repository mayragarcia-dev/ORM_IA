# Diagrama de Relaciones - Blog App

## Entidades y Relaciones

```
┌─────────────────┐       ┌──────────────────────┐
│     Author      │       │    AuthorProfile     │
├─────────────────┤       ├──────────────────────┤
│ id (PK)         │◄──────│ id (PK)              │
│ name            │  1:1  │ author_id (FK, UNIQUE)│
│ email (unique)  │       │ avatar               │
│ bio             │       │ website              │
│ created_at      │       │ twitter              │
└────────┬────────┘       │ github               │
         │                │ created_at           │
         │                │ updated_at           │
         │                └──────────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐       ┌──────────────────────┐
│    Article      │       │     Category         │
├─────────────────┤       ├──────────────────────┤
│ id (PK)         │       │ id (PK)              │
│ title           │       │ name (unique)        │
│ slug (unique)   │       │ slug (unique)        │
│ content         │       │ description          │
│ author_id (FK)  │───────│ created_at           │
│ category_id(FK) │ N:1   └──────────────────────┘
│ published_at    │  (opcional, null=True)
│ updated_at      │
│ is_published    │       ┌──────────────────────┐
└────────┬────────┘       │        Tag           │
         │                ├──────────────────────┤
         │ M:N            │ id (PK)              │
         ├────────────────│ name (unique)        │
         │                │ slug (unique)        │
         │                │ created_at           │
         │                └──────────┬───────────┘
         │                           │
         │                    ┌──────┴──────┐
         │                    │ Article_Tags │
         │                    │ (tabla intermedia)│
         │                    ├───────────────┤
         │                    │ id (PK)       │
         │                    │ article_id(FK)│
         │                    │ tag_id (FK)   │
         │                    └───────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐
│    Comment      │
├─────────────────┤
│ id (PK)         │
│ article_id (FK) │
│ author_name     │
│ author_email    │
│ content         │
│ created_at      │
│ is_approved     │
└─────────────────┘
```

## Detalle de Relaciones

### 1. Author ↔ AuthorProfile (OneToOne)
- **Author.profile** → `related_name='profile'`
- **AuthorProfile.author** → `OneToOneField(Author, on_delete=CASCADE)`
- Cada autor tiene **exactamente un** perfil (o ninguno si no se crea)
- Eliminar Author elimina su Profile (CASCADE)

### 2. Author → Article (OneToMany / ForeignKey)
- **Author.articles** → `related_name='articles'`
- **Article.author** → `ForeignKey(Author, on_delete=CASCADE)`
- Un autor puede tener **muchos artículos**
- Eliminar Author elimina sus artículos (CASCADE)

### 3. Category → Article (OneToMany, opcional)
- **Category.articles** → `related_name='articles'`
- **Article.category** → `ForeignKey(Category, on_delete=SET_NULL, null=True, blank=True)`
- Un artículo **puede no tener categoría** (null=True, blank=True)
- Eliminar Category pone NULL en los artículos (SET_NULL)

### 4. Article ↔ Tag (ManyToMany)
- **Article.tags** → `ManyToManyField(Tag, blank=True, related_name='articles')`
- **Tag.articles** → `related_name='articles'`
- Tabla intermedia automática: `blog_app_article_tags`
- Un artículo puede tener **múltiples etiquetas**
- Una etiqueta puede estar en **múltiples artículos**
- `blank=True` → artículo puede tener 0 etiquetas

### 5. Article → Comment (OneToMany / ForeignKey)
- **Article.comments** → `related_name='comments'`
- **Comment.article** → `ForeignKey(Article, on_delete=CASCADE)`
- Un artículo tiene **muchos comentarios**
- Eliminar Article elimina sus comentarios (CASCADE)
- Comentarios tienen `is_approved` para moderación

## Cardinalidades Resumidas

| Relación | Tipo | Obligatorio | On Delete |
|----------|------|-------------|-----------|
| Author → AuthorProfile | 1:1 | No (profile opcional) | CASCADE |
| Author → Article | 1:N | Sí (FK not null) | CASCADE |
| Category → Article | 1:N | No (null/blank=True) | SET_NULL |
| Article ↔ Tag | M:N | No (blank=True) | CASCADE (tabla intermedia) |
| Article → Comment | 1:N | Sí (FK not null) | CASCADE |

## Consultas Típicas de Navegación

```python
# Autor → Perfil
author.profile

# Autor → Artículos
author.articles.all()

# Artículo → Autor
article.author

# Artículo → Categoría (puede ser None)
article.category

# Artículo → Etiquetas
article.tags.all()

# Artículo → Comentarios aprobados
article.comments.filter(is_approved=True)

# Categoría → Artículos
category.articles.all()

# Etiqueta → Artículos
tag.articles.all()

# Comentario → Artículo
comment.article
```

## Índices y Constraints Implícitos

- `Author.email` → UNIQUE
- `Category.name`, `Category.slug` → UNIQUE
- `Tag.name`, `Tag.slug` → UNIQUE
- `Article.slug` → UNIQUE
- `AuthorProfile.author` → UNIQUE (OneToOne)
- FKs crean índices automáticos en Django