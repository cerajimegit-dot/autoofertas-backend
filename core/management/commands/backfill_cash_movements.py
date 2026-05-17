"""Genera CashMovement automáticos para ventas y cuotas ya existentes.

Idempotente: si el movimiento ya existe, lo saltea (matching por sale+kind
o quota+kind). Se puede correr múltiples veces.

Uso:
    python manage.py backfill_cash_movements
    python manage.py backfill_cash_movements --enterprise 3
    python manage.py backfill_cash_movements --dry-run
"""

from datetime import date as _date
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Sale, Quotum, CashMovement


class Command(BaseCommand):
    help = 'Genera CashMovement para Sale.completed y Quotum.paid ya existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--enterprise', type=int, default=None,
                            help='Filtrar a una enterprise específica.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Reporta lo que haría sin escribir nada.')

    def handle(self, *args, **opts):
        ent_id = opts.get('enterprise')
        dry = opts.get('dry_run', False)

        sales_qs = Sale.objects.filter(status='completed').select_related(
            'payment_form', 'branch', 'seller'
        )
        quotas_qs = Quotum.objects.filter(status='paid').exclude(
            payment_date__isnull=True
        ).select_related('sale', 'sale__branch', 'customer')

        if ent_id:
            sales_qs = sales_qs.filter(enterprise_id=ent_id)
            quotas_qs = quotas_qs.filter(enterprise_id=ent_id)

        self.stdout.write(self.style.NOTICE(
            f'Sales completadas: {sales_qs.count()}, '
            f'Cuotas paid con fecha: {quotas_qs.count()}'
        ))

        if dry:
            self.stdout.write(self.style.WARNING('DRY-RUN — no se escribe nada.'))

        # ---------------- Ventas ----------------
        n_contado = n_sena = n_skip = 0
        existing_sale_contado = set(
            CashMovement.objects.filter(kind='venta_contado', sale__isnull=False)
                                .values_list('sale_id', flat=True)
        )
        existing_sale_sena = set(
            CashMovement.objects.filter(kind='seña_credito', sale__isnull=False)
                                .values_list('sale_id', flat=True)
        )

        sale_movements = []
        for s in sales_qs.iterator(chunk_size=200):
            pf = (s.payment_form.name.upper() if s.payment_form else '')
            sale_date = s.sale_date.date() if hasattr(s.sale_date, 'date') else s.sale_date

            if 'CONTADO' in pf and s.id not in existing_sale_contado:
                sale_movements.append(CashMovement(
                    enterprise_id=s.enterprise_id, branch_id=s.branch_id,
                    sale=s, kind='venta_contado', direction='in',
                    amount=s.total_price, date=sale_date,
                    description=f'Venta contado {s.sale_number}',
                    is_auto=True, created_by=s.seller,
                ))
                n_contado += 1
            elif s.id in existing_sale_contado:
                n_skip += 1

            if s.down_payment and float(s.down_payment) > 0 and s.id not in existing_sale_sena:
                sale_movements.append(CashMovement(
                    enterprise_id=s.enterprise_id, branch_id=s.branch_id,
                    sale=s, kind='seña_credito', direction='in',
                    amount=s.down_payment, date=sale_date,
                    description=f'Seña venta {s.sale_number}',
                    is_auto=True, created_by=s.seller,
                ))
                n_sena += 1
            elif s.id in existing_sale_sena:
                n_skip += 1

        if not dry and sale_movements:
            CashMovement.objects.bulk_create(sale_movements, batch_size=500)
        self.stdout.write(self.style.SUCCESS(
            f'  Sales -> venta_contado: {n_contado}, seña_credito: {n_sena}, '
            f'ya existían: {n_skip}'
        ))

        # ---------------- Cuotas ----------------
        n_cuotas = n_skip_q = 0
        existing_quota = set(
            CashMovement.objects.filter(kind='cobro_cuota', quota__isnull=False)
                                .values_list('quota_id', flat=True)
        )

        quota_movements = []
        for q in quotas_qs.iterator(chunk_size=500):
            if q.id in existing_quota:
                n_skip_q += 1
                continue
            customer_name = q.customer.full_name if q.customer else 'sin cliente'
            sale_number = q.sale.sale_number if q.sale else ''
            quota_movements.append(CashMovement(
                enterprise_id=q.enterprise_id,
                branch_id=q.sale.branch_id if q.sale else None,
                quota=q, kind='cobro_cuota', direction='in',
                amount=q.amount, date=q.payment_date,
                description=(
                    f'Cuota {q.quota_number}'
                    f'{("/" + str(q.total_plan)) if q.total_plan else ""} '
                    f'venta {sale_number} — {customer_name}'
                ),
                is_auto=True,
                notes='migrado, fecha aproximada' if q.payment_date < _date(2024, 1, 1) else '',
            ))
            n_cuotas += 1

        if not dry and quota_movements:
            CashMovement.objects.bulk_create(quota_movements, batch_size=500)
        self.stdout.write(self.style.SUCCESS(
            f'  Quotas -> cobro_cuota: {n_cuotas}, ya existían: {n_skip_q}'
        ))

        total = n_contado + n_sena + n_cuotas
        self.stdout.write(self.style.NOTICE(
            f'\nTotal movimientos {"a crear" if dry else "creados"}: {total}'
        ))
