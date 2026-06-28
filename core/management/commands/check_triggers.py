from django.core.management.base import BaseCommand
from core.services import process_expired_triggers


class Command(BaseCommand):
    help = 'Revisa y ejecuta triggers vencidos del Dead Man Switch'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo mostrar qué triggers se activarían')

    def handle(self, *args, **options):
        results = process_expired_triggers(dry_run=options['dry_run'])
        for r in results:
            self.stdout.write(r)
