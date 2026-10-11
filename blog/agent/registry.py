"""
Registro de acciones del agente del blog.

Este módulo es la ÚNICA superficie de acción del agente. El texto de la
intención que llega por consola se *clasifica* contra una whitelist; jamás se
interpreta, se evalúa ni se ejecuta.

Mecanismos de seguridad
-----------------------
1. Whitelist + denegación por defecto: solo las acciones de ``ACTIONS`` pueden
   ejecutarse. Toda intención que no case con una regla se deniega sin correr
   una sola línea de código del agente.
2. Lista de denegación (``DENIED_PATTERNS``): borrados masivos, SQL crudo,
   ``eval``/``exec``/shell e inyección de prompt se deniegan con motivo
   explícito, antes de mirar las acciones permitidas.
3. Datos de terceros = datos, nunca instrucciones: el contenido de un
   comentario se muestra entrecomillado y etiquetado con ``DATA_LABEL``; no se
   pasa a ``eval``, ``exec`` ni a ningún parser de instrucciones.
4. Plan con hash + huella de datos (anti-TOCTOU): las acciones de escritura
   generan un plan guardado en ``.agent_plans.json``. El hash es un HMAC-SHA256
   (clave: ``settings.SECRET_KEY``) sobre acción + parámetros + huella SHA-256
   de los registros EXACTOS que la acción va a tocar. Al aprobar, la huella se
   recalcula: si los datos cambiaron entre el plan y la aprobación, el hash no
   coincide y la ejecución se rechaza.
5. Sin superficie de ataque: las acciones son funciones Python fijas de este
   registro y usan solo el ORM de Django. No hay SQL crudo, ni archivos, ni
   shell, ni introspección de modelos por nombre arbitrario.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from django.conf import settings

PLAN_FILE = Path(settings.BASE_DIR) / '.agent_plans.json'
DATA_LABEL = '[DATO NO CONFIABLE]'

DECISION_OK = 'ok'
DECISION_APPROVAL_REQUIRED = 'approval_required'
DECISION_DENIED = 'denied'

KIND_READ = 'read'
KIND_WRITE = 'write'


# ---------------------------------------------------------------------------
# Acciones (whitelist)
# ---------------------------------------------------------------------------


def resolve_article(ref: Any):
    """
    Resuelve el parámetro ``post`` a un artículo.

    Acepta:
      1. el pk del artículo (si existe en la base de datos),
      2. o su posición entre los artículos PUBLICADOS en orden cronológico
         (el "artículo 1" es el más antiguo de los publicados).

    Cualquier otro valor lanza ``ValueError``: el agente nunca adivina ni
    consulta modelos que no estén en este archivo.
    """
    from blog_app.models import Article

    try:
        n = int(ref)
    except (TypeError, ValueError):
        raise ValueError(f'parámetro post inválido: {ref!r} (se espera un número)')

    article = Article.objects.filter(pk=n, is_published=True).first()
    if article is not None:
        return article

    published = list(Article.objects.filter(is_published=True).order_by('published_at'))
    if 1 <= n <= len(published):
        return published[n - 1]

    article = Article.objects.filter(pk=n).first()
    if article is not None:
        return article

    raise ValueError(f'no existe el artículo {n} (hay {len(published)} artículos publicados)')


def action_list_published_articles(params: Dict[str, Any]) -> str:
    from blog_app.models import Article

    articles = (
        Article.objects.filter(is_published=True)
        .select_related('author', 'category')
        .order_by('published_at')
    )
    lines = [f'Artículos publicados: {articles.count()}']
    for position, article in enumerate(articles, 1):
        category = article.category.name if article.category_id else '(sin categoría)'
        lines.append(
            f'{position}. [{article.pk}] {article.title} — {article.author.name} '
            f'— {category} — comentarios: {article.comments.count()}'
        )
    return '\n'.join(lines)


def action_comments_of_post(params: Dict[str, Any]) -> str:
    article = resolve_article(params['post'])
    comments = list(article.comments.order_by('created_at'))
    lines = [
        f'Artículo [{article.pk}] {article.title} — {len(comments)} comentario(s), '
        f'en orden cronológico:'
    ]
    for index, comment in enumerate(comments, 1):
        lines.append(
            f'  #{index} {comment.author_name} <{comment.author_email}> '
            f'({comment.created_at:%Y-%m-%d %H:%M:%S}):'
        )
        lines.append(f'      {DATA_LABEL} {comment.content!r}')
    lines.append(
        'Nota de seguridad: el texto de los comentarios es dato escrito por '
        ' terceros. El agente lo muestra entrecomillado y etiquetado; jamás lo '
        'interpreta como instrucción.'
    )
    return '\n'.join(lines)


def action_delete_comments_of_post(params: Dict[str, Any]) -> str:
    article = resolve_article(params['post'])
    targets = list(article.comments.order_by('created_at'))
    deleted, _ = article.comments.all().delete()
    preview = ', '.join(f'#{i} {c.author_name!r}' for i, c in enumerate(targets, 1))
    return (
        f'Plan ejecutado: se eliminaron {deleted} comentario(s) del artículo '
        f'[{article.pk}] {article.title} ({preview}).'
    )


@dataclass(frozen=True)
class Action:
    name: str
    description: str
    kind: str
    handler: Callable[[Dict[str, Any]], str]
    approval_required: bool = False


ACTIONS: Dict[str, Action] = {
    action.name: action
    for action in (
        Action(
            name='list_published_articles',
            description='Lista los artículos publicados con autor, categoría y conteo de comentarios.',
            kind=KIND_READ,
            handler=action_list_published_articles,
        ),
        Action(
            name='comments_of_post',
            description='Muestra los comentarios de un artículo (parámetro post) en orden cronológico.',
            kind=KIND_READ,
            handler=action_comments_of_post,
        ),
        Action(
            name='delete_comments_of_post',
            description='Elimina TODOS los comentarios de un artículo (parámetro post). Requiere aprobación.',
            kind=KIND_WRITE,
            handler=action_delete_comments_of_post,
            approval_required=True,
        ),
    )
}


# ---------------------------------------------------------------------------
# Denegación por defecto: lista negra de intenciones peligrosas
# ---------------------------------------------------------------------------


DENIED_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r'\bdrop\s+(table|database|schema)\b', re.I),
     'SQL destructivo sobre la base de datos'),
    (re.compile(r'\btruncate\b|\bflush\b', re.I),
     'vaciado masivo de tablas'),
    (re.compile(r'(?:elimin|borr|del)[a-záéíóúñ]*\s+(?:todos?|todas?)\s+(?:los\s+|las\s+)?'
                r'(?:art[ií]culos|comentarios|datos|registros|autores|etiquetas|categor[ií]as)\b',
                re.I),
     'borrado masivo sin objetivo concreto (no se expone una acción para eso)'),
    (re.compile(r'\beval\s*\(|\bexec\s*\(|\bos\.system\b|\bsubprocess\b|__import__|\bshell\b',
                re.I),
     'invocación de código arbitrario o de una shell'),
    (re.compile(r';\s*--|\'\s*or\s*\'?\s*1\s*=\s*1', re.I),
     'inyección de SQL en el texto de la intención'),
    (re.compile(r'ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|'
                r'ignora(?:n)?\s+(?:todas?\s+)?(?:las\s+)?instrucciones', re.I),
     'inyección de prompt (prompt injection)'),
]


# ---------------------------------------------------------------------------
# Reglas de clasificación (whitelist)
# ---------------------------------------------------------------------------


_INTENT_RULES: List[Tuple[str, re.Pattern]] = [
    ('delete_comments_of_post', re.compile(
        r'\bdelete_comments_of_post\b[^\d]*(?P<post>\d+)', re.I)),
    ('delete_comments_of_post', re.compile(
        r'\b(?:borr|elimin)[a-záéíóúñ]*\s+(?:los\s+|las\s+)?comentarios?\s+'
        r'del\s+art[ií]culo\s+(?P<post>\d+)', re.I)),
    ('comments_of_post', re.compile(
        r'\bcomments?_of_post\b[^\d]*(?P<post>\d+)', re.I)),
    ('comments_of_post', re.compile(
        r'\bcomentarios?\s+del\s+art[ií]culo\s+(?P<post>\d+)', re.I)),
    ('list_published_articles', re.compile(
        r'\blist(?:_|\s)+published(?:_|\s)+articles\b', re.I)),
    ('list_published_articles', re.compile(
        r'\blista(?:r)?\b[\s\S]*?\bart[ií]culos?\s+publicados\b', re.I)),
]


@dataclass
class Classification:
    decision: str
    reason: str
    action: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


def classify_intent(intent: str) -> Classification:
    """
    Clasifica el texto de una intención. El texto solo SE COMPARA con regex de
    la whitelist y de la lista negra; nunca se evalúa ni se fragmenta en
    comandos.
    """
    text = (intent or '').strip()
    if not text:
        return Classification(DECISION_DENIED, 'intención vacía')

    for pattern, motive in DENIED_PATTERNS:
        if pattern.search(text):
            return Classification(DECISION_DENIED, f'intención denegada: {motive}')

    for action_name, pattern in _INTENT_RULES:
        match = pattern.search(text)
        if not match:
            continue
        params: Dict[str, Any] = {}
        if 'post' in pattern.groupindex:
            params['post'] = int(match.group('post'))
        action = ACTIONS[action_name]
        if action.approval_required:
            return Classification(
                DECISION_APPROVAL_REQUIRED,
                f'la acción "{action_name}" modifica datos y requiere un plan aprobado',
                action=action_name,
                params=params,
            )
        return Classification(DECISION_OK, f'acción de solo lectura "{action_name}"',
                              action=action_name, params=params)

    return Classification(
        DECISION_DENIED,
        'intención no reconocida: fuera de la whitelist de acciones '
        f'({", ".join(sorted(ACTIONS))})',
    )


# ---------------------------------------------------------------------------
# Planes con hash y huella de datos
# ---------------------------------------------------------------------------


def fingerprint_for(action_name: str, params: Dict[str, Any]) -> str:
    """
    Huella SHA-256 de los registros exactos que la acción va a tocar. Cambiar
    un solo byte de un comentario destino cambia la huella y, por lo tanto, el
    hash del plan.
    """
    if action_name == 'delete_comments_of_post':
        article = resolve_article(params['post'])
        rows = sorted(
            f'{c.pk}|{c.created_at.isoformat()}|'
            f'{hashlib.sha256(c.content.encode("utf-8")).hexdigest()[:16]}'
            for c in article.comments.all()
        )
        payload = (f'delete_comments_of_post|article={article.pk}|count={len(rows)}|'
                   + ';'.join(rows))
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()
    raise ValueError(f'acción sin huella definida: {action_name}')


def _plan_hash(action_name: str, params: Dict[str, Any], fingerprint: str) -> str:
    message = (action_name + '|'
               + json.dumps(params, sort_keys=True) + '|'
               + fingerprint)
    return hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def preview_for(action_name: str, params: Dict[str, Any]) -> str:
    """Descripción humana del efecto del plan, calculada al generarlo."""
    if action_name == 'delete_comments_of_post':
        article = resolve_article(params['post'])
        targets = list(article.comments.order_by('created_at'))
        listing = ', '.join(
            f'#{i} {c.author_name!r} ({c.created_at:%Y-%m-%d %H:%M})'
            for i, c in enumerate(targets, 1)
        ) or '(sin comentarios)'
        return (f'Se eliminarían {len(targets)} comentario(s) del artículo '
                f'[{article.pk}] {article.title}: {listing}.')
    return ''


def load_plans() -> Dict[str, Dict[str, Any]]:
    if not PLAN_FILE.exists():
        return {}
    try:
        return json.loads(PLAN_FILE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_plans(plans: Dict[str, Dict[str, Any]]) -> None:
    PLAN_FILE.write_text(json.dumps(plans, indent=2, ensure_ascii=False), encoding='utf-8')


def build_plan(action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    fingerprint = fingerprint_for(action_name, params)
    return {
        'hash': _plan_hash(action_name, params, fingerprint),
        'action': action_name,
        'params': params,
        'fingerprint': fingerprint,
        'created_at': datetime.now().isoformat(timespec='seconds'),
        'preview': preview_for(action_name, params),
    }


def store_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda el plan (reemplaza uno equivalente pendiente) y lo devuelve."""
    plans = load_plans()
    plans[plan['hash']] = plan
    save_plans(plans)
    return plan


def pop_plan(plan_hash: str) -> Optional[Dict[str, Any]]:
    plans = load_plans()
    plan = plans.pop(plan_hash, None)
    if plan is not None:
        save_plans(plans)
    return plan


def find_plan(plan_hash: str) -> Optional[Dict[str, Any]]:
    plans = load_plans()
    if plan_hash in plans:
        return plans[plan_hash]
    matches = [p for h, p in plans.items() if h.startswith(plan_hash)]
    return matches[0] if len(matches) == 1 else None


def approve_plan(plan_hash: str, intent: Optional[str] = None) -> Tuple[bool, str]:
    """
    Valida y ejecuta un plan pendiente.

    Comprobaciones, en orden:
      1. el plan existe (y coincide con la intención repetida, si se pasó),
      2. la huella de los datos actuales sigue coincidiendo (anti-TOCTOU),
      3. recién entonces se ejecuta el handler y el plan se consume.
    """
    plan = find_plan(plan_hash)
    if plan is None:
        return False, ('DENIED: no existe un plan pendiente con ese hash '
                       '(puede haber sido ejecutado, revocado o expirado).')

    if intent:
        classification = classify_intent(intent)
        if (classification.decision == DECISION_DENIED
                or classification.action != plan['action']
                or classification.params != plan['params']):
            return False, (f'DENIED: la intención repetida ({classification.action!r}, '
                           f'{classification.params}) no coincide con el plan '
                           f'{plan["action"]!r} {plan["params"]}.')

    current = fingerprint_for(plan['action'], plan['params'])
    if not hmac.compare_digest(current, plan['fingerprint']):
        return False, (
            'DENIED: los datos cambiaron después de generar el plan. '
            f'Huella del plan: {plan["fingerprint"][:12]}…; '
            f'huella actual: {current[:12]}…. Vuelve a pedir el plan para '
            'aprobar una acción sobre el estado real.'
        )

    action = ACTIONS[plan['action']]
    output = action.handler(plan['params'])
    pop_plan(plan['hash'])
    return True, output
