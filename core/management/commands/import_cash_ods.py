"""Importa un archivo "FLUJO DE CAJA …".ods al modelo CashMovement.

Uso:
    python manage.py import_cash_ods <ruta.ods> --enterprise=3
    python manage.py import_cash_ods <ruta.ods> --enterprise=3 --branch=1
    python manage.py import_cash_ods <ruta.ods> --enterprise=3 --dry-run
"""

from django.core.management.base import BaseCommand, CommandError

from core.models import Enterprise, Branch
from core.services.cash_import import import_ods_to_cash_movements


class Command(BaseCommand):
    help = 'Importa un archivo ODS de flujo de caja al modelo CashMovement.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Ruta al archivo .ods')
        parser.add_argument('--enterprise', type=int, required=True,
                            help='ID de la empresa destino.')
        parser.add_argument('--branch', type=int, default=None,
                            help='ID de sucursal por defecto para los movimientos.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Reporta sin escribir nada.')

    def handle(self, *args, **opts):
        path = opts['file_path']
        ent_id = opts['enterprise']
        branch_id = opts.get('branch')
        dry = opts.get('dry_run', False)

        try:
            ent = Enterprise.objects.get(pk=ent_id)
        except Enterprise.DoesNotExist:
            raise CommandError(f'Enterprise id={ent_id} no existe')

        branch = None
        if branch_id:
            try:
                branch = Branch.objects.get(pk=branch_id, enterprise=ent)
            except Branch.DoesNotExist:
                raise CommandError(f'Branch id={branch_id} no pertenece a esta empresa')

        if dry:
            self.stdout.write(self.style.WARNING('DRY-RUN — no se escribe nada.'))

        result = import_ods_to_cash_movements(
            path, enterprise=ent, branch=branch, dry_run=dry,
        )

        self.stdout.write('')
        self.stdout.write(f'Total filas en ODS:         {result["total_rows"]}')
        self.stdout.write(f'  - sin fecha/monto:        {result["invalid_rows"]}')
        self.stdout.write(f'  - ya en sistema (auto):   {result["skipped_auto"]}')
        self.stdout.write(self.style.SUCCESS(
            f'  - manuales {"a crear" if dry else "creadas"}:        {result["created_manual"]}'
        ))

        if result['unclassified']:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                f'{len(result["unclassified"])} fila(s) sin clasificar — se crearon como "otro":'
            ))
            for u in result['unclassified'][:15]:
                self.stdout.write(f'  fila {u["row"]:>3}: {u["date"]} {u["amount"]:>15,.0f}  {u["op"][:60]}')

        if dry and result['created']:
            self.stdout.write('')
            self.stdout.write('Detalle de movimientos a crear:')
            for c in result['created'][:30]:
                signo = '-' if c['direction'] == 'out' else '+'
                self.stdout.write(
                    f'  {c["date"]} {c["kind"]:18s} {signo}{c["amount"]:>13,.0f}  {c["op"]}'
                )
            if len(result['created']) > 30:
                self.stdout.write(f'  ... ({len(result["created"]) - 30} más)')
