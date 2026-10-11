"""
Agente del blog.

Clasifica el texto de una intención contra la whitelist de
``blog/agent/registry.py`` y decide qué hacer:

  - ok:               acción de solo lectura, se ejecuta de inmediato.
  - approval_required: acción de escritura; genera un PLAN con hash que debe
                       aprobarse con ``--approve <HASH>``.
  - denied:           fuera de la whitelist o en la lista negra; no se ejecuta
                       absolutamente nada.

El texto de la intención NUNCA se evalúa ni se fragmenta en comandos: solo se
compara con regex del registro. Los datos de terceros (p. ej. el texto de un
comentario) se muestran etiquetados como ``[DATO NO CONFIABLE]``.

Uso:
    python manage.py agent --intent 'lista los artículos publicados'
    python manage.py agent --intent 'muestra los comentarios del artículo 1'
    python manage.py agent --intent 'borra los comentarios del artículo 5'
    python manage.py agent --intent '...' --approve <HASH>
    python manage.py agent --list-actions
    python manage.py agent --list-plans
    python manage.py agent --revoke <HASH>
"""

from django.core.management.base import BaseCommand, CommandError

from blog.agent import registry


class Command(BaseCommand):
    help = 'Clasifica una intención y ejecuta solo las acciones registradas en blog/agent/registry.py.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--intent', type=str, default=None,
            help="Texto de la intención (p. ej. 'lista los artículos publicados').",
        )
        parser.add_argument(
            '--approve', metavar='HASH', default=None,
            help='Aprueba y ejecuta un plan pendiente por su hash.',
        )
        parser.add_argument(
            '--revoke', metavar='HASH', default=None,
            help='Descarta un plan pendiente sin ejecutarlo.',
        )
        parser.add_argument(
            '--list-actions', action='store_true',
            help='Lista las acciones de la whitelist.',
        )
        parser.add_argument(
            '--list-plans', action='store_true',
            help='Lista los planes pendientes de aprobación.',
        )

    # ------------------------------------------------------------------ #

    def handle(self, *args, **options):
        if options['list_actions']:
            return self._list_actions()
        if options['list_plans']:
            return self._list_plans()
        if options['revoke']:
            return self._revoke(options['revoke'])
        if options['approve']:
            return self._approve(options['approve'], options['intent'])
        if options['intent']:
            return self._run_intent(options['intent'])
        raise CommandError(
            "Falta la intención. Usa --intent '...', --approve HASH, "
            '--revoke HASH, --list-actions o --list-plans.'
        )

    # ------------------------------------------------------------------ #

    def _list_actions(self):
        self.stdout.write(self.style.NOTICE('=== Whitelist de acciones ==='))
        for name, action in registry.ACTIONS.items():
            mode = 'escritura (requiere aprobación)' if action.approval_required else 'lectura'
            self.stdout.write(f'- {name} [{mode}]: {action.description}')

    def _list_plans(self):
        plans = registry.load_plans()
        self.stdout.write(self.style.NOTICE('=== Planes pendientes ==='))
        if not plans:
            self.stdout.write('(no hay planes pendientes)')
            return
        for plan in plans.values():
            self.stdout.write(
                f'- {plan["hash"][:16]}… creado {plan["created_at"]}: '
                f'{plan["action"]} {plan["params"]}'
            )
            self.stdout.write(f'    {plan["preview"]}')

    def _revoke(self, plan_hash):
        plan = registry.pop_plan(plan_hash)
        if plan is None:
            raise CommandError(f'No hay plan pendiente con hash {plan_hash}.')
        self.stdout.write(self.style.SUCCESS(
            f'Plan {plan["hash"][:16]}… revocado sin ejecutarse.'
        ))

    # ------------------------------------------------------------------ #

    def _run_intent(self, intent):
        self.stdout.write(self.style.NOTICE('=== Agente del blog ==='))
        self.stdout.write(f'Intención recibida: {intent!r}')
        self.stdout.write(
            ' (el texto solo se clasifica contra la whitelist; no se ejecuta)'
        )

        classification = registry.classify_intent(intent)
        self.stdout.write(f'Clasificación: acción={classification.action} '
                          f'parámetros={classification.params}')
        self.stdout.write(f'Motivo: {classification.reason}')

        if classification.decision == registry.DECISION_DENIED:
            self.stdout.write(self.style.ERROR('Veredicto: denied'))
            self.stdout.write('No se ejecutó ninguna acción.')
            return

        if classification.decision == registry.DECISION_APPROVAL_REQUIRED:
            plan = registry.build_plan(classification.action, classification.params)
            registry.store_plan(plan)
            self.stdout.write(self.style.WARNING('Veredicto: approval_required'))
            self.stdout.write('La acción modifica datos; NO se ejecutó todavía.')
            self.stdout.write(f'  Acción:   {plan["action"]} {plan["params"]}')
            self.stdout.write(f'  Huella:   {plan["fingerprint"][:16]}…')
            self.stdout.write(f'  Efecto:   {plan["preview"]}')
            self.stdout.write(self.style.SUCCESS(f'  Hash del plan: {plan["hash"]}'))
            self.stdout.write(
                "Para ejecutarlo: python manage.py agent --intent "
                f"{intent!r} --approve {plan['hash']}"
            )
            return

        action = registry.ACTIONS[classification.action]
        try:
            output = action.handler(classification.params)
        except ValueError as exc:
            self.stdout.write(self.style.ERROR('Veredicto: denied'))
            self.stdout.write(f'Motivo: {exc}')
            return
        self.stdout.write(self.style.SUCCESS('Veredicto: ok'))
        self.stdout.write(output)

    # ------------------------------------------------------------------ #

    def _approve(self, plan_hash, intent):
        self.stdout.write(self.style.NOTICE('=== Aprobación de plan ==='))
        self.stdout.write(f'Hash recibido: {plan_hash}')
        try:
            ok, message = registry.approve_plan(plan_hash, intent)
        except ValueError as exc:
            self.stdout.write(self.style.ERROR('Veredicto: denied'))
            self.stdout.write(f'Motivo: {exc}')
            return
        if ok:
            self.stdout.write(self.style.SUCCESS('Veredicto: ok (plan ejecutado)'))
            self.stdout.write(message)
        else:
            self.stdout.write(self.style.ERROR('Veredicto: denied'))
            self.stdout.write(message)
