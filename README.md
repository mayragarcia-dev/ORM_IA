# ORM_IA — Blog Django (Lab 07: ORM + IA)

Proyecto Django de un blog con autores, perfiles (1:1), categorías, etiquetas
(M2M) y comentarios. El laboratorio cubre consultas ORM (duelo de 8 preguntas),
optimización N+1 y un **agente de IA con seguridad** (acciones whitelistadas,
planificación con hash y aprobación explícita).

## Puesta en marcha

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_blog     # datos siempre iguales: 5 autores, 5 perfiles,
                                # 5 categorías, 9 etiquetas, 8 artículos (7 publicados)
                                # y 13 comentarios
```

## Duelo ORM (8 preguntas)

```bash
python manage.py duel                     # respuestas del equipo  → 8/8
python manage.py duel --source ai         # respuestas de la IA (paso 6)
python manage.py duel --source assistant  # respuestas de la IA desde cero (paso 8)
python manage.py duel --sql               # imprime el SQL de cada consulta
```

## Pruebas (N+1)

```bash
python manage.py test blog.tests.test_front_page   # portada en 2 consultas
python manage.py test                               # suite completa
```

## Agente del blog (`manage.py agent`)

El agente **no interpreta ni ejecuta** el texto que recibe: solo lo *clasifica*
contra una whitelist de acciones registradas en `blog/agent/registry.py`.
Las acciones de escritura no se ejecutan solas: generan un **plan** con un
**hash** (HMAC sobre acción + parámetros + huella de los datos que va a tocar)
que debe aprobarse con `--approve`. Si los datos cambian entre el plan y la
aprobación, el hash deja de coincidir y la aprobación se rechaza.

### Las cuatro intenciones documentadas

| # | Intención | Comando | Veredicto esperado |
|---|-----------|---------|--------------------|
| 1 | Listar artículos publicados (lectura) | `python manage.py agent --intent 'lista los artículos publicados'` | `ok` |
| 2 | Ver comentarios del artículo 1 (lectura) | `python manage.py agent --intent 'muestra los comentarios del artículo 1'` | `ok` |
| 3 | Borrar los comentarios del artículo 5 (escritura) | `python manage.py agent --intent 'borra los comentarios del artículo 5'` | `approval_required` |
| 4 | Borrar todos los artículos y comentarios (destructiva masiva) | `python manage.py agent --intent 'elimina todos los artículos y comentarios de la base de datos'` | `denied` |

La intención 3 se completa con el hash que imprime el agente:

```bash
python manage.py agent --intent 'borra los comentarios del artículo 5' --approve <HASH>
```

Otras utilidades:

```bash
python manage.py agent --list-actions    # acciones registradas (whitelist)
python manage.py agent --list-plans      # planes pendientes de aprobación
python manage.py agent --revoke <HASH>   # descarta un plan pendiente
```

### Parámetro `post`

En `comments_of_post` / `delete_comments_of_post` el parámetro `post` acepta:

1. el **pk** del artículo (si existe),
2. o su **posición** entre los artículos publicados, en orden cronológico
   (el "artículo 1" es *Introducción a Django ORM*; el "artículo 5" es
   *Relaciones Many-to-Many en Django*).

### Mecanismos de seguridad de `blog/agent/registry.py`

1. **Whitelist / denegación por defecto**: solo las acciones registradas pueden
   ejecutarse; cualquier intención no reconocida se deniega sin ejecutar nada.
2. **Lista de denegación**: operaciones destructivas masivas, SQL crudo,
   `eval`/`exec`/shell e inyección de prompt se deniegan con motivo explícito.
3. **Datos de terceros = datos, nunca instrucciones**: el texto de un
   comentario se muestra entrecomillado y etiquetado como
   `[DATO NO CONFIABLE]`; jamás se pasa a `eval`, `exec` ni a un parser.
4. **Plan con hash + huella de datos (anti-TOCTOU)**: el hash cubre acción,
   parámetros y una huella SHA-256 de los registros exactos que se van a
   modificar; al aprobar se recalcula y se compara.
5. **Sin superficie de ataque**: las acciones son funciones Python fijas del
   registro que usan solo el ORM; no hay acceso a SQL crudo, archivos ni shell.

## Documentación

- `DIAGRAMA_RELACIONES.md` — diagrama de relaciones del modelo.
- `DUEL_RESULTS.md` — intentos del duelo ORM.
- `ENTREGABLE.md` — entregable completo: pasos 6 a 15 (IA, N+1, agente y cierre).
