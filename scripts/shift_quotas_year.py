"""Suma N años a la `due_date` de TODAS las cuotas de una o más ventas.

Caso típico: venta cargada en diciembre 2025 cuyo plan de cuotas se generó
con vencimientos en 2025 (1/1/2025, 1/2/2025...) en lugar de 2026.
Solución: aplicar shift de +1 año a todas las cuotas de esa venta.

POR DEFAULT NO TOCA NADA — es dry-run. Imprime qué cambiaría y termina.
Para aplicar de verdad, agregar el flag `--confirm`.

Funciona contra SQLite local (DB_ENGINE=sqlite) o Postgres / Supabase
(DB_ENGINE=postgres) — usa el ORM, agnostic.

USO:
    # Dry-run, 1 año:
    DB_ENGINE=sqlite python scripts/shift_quotas_year.py MC56/25

    # Aplicar de verdad:
    DB_ENGINE=sqlite python scripts/shift_quotas_year.py MC56/25 --confirm

    # Varias ventas en una corrida:
    python scripts/shift_quotas_year.py MC56/25 CM12/25 --confirm

    # Shift custom (ej. -2 años, o 6 meses):
    python scripts/shift_quotas_year.py MC56/25 --years -2 --confirm
    python scripts/shift_quotas_year.py MC56/25 --months 6 --confirm

SEGURIDAD:
  - Sólo modifica `due_date` de las cuotas. No toca montos ni status.
  - Pide doble confirmación cuando se corre con --confirm contra una BD
    que NO sea SQLite (asumimos que Postgres = producción).
  - Imprime un audit trail con id de cuota + fecha vieja + fecha nueva.

NO TOCA:
  - Cuotas con due_date NULL.
  - Si --status-pending se pasa: sólo cuotas que aún no fueron cobradas
    (status='pending' u 'overdue'). Útil si querés conservar el historial
    de las cuotas ya pagadas con su due_date original.
"""

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from django.db import transaction, connection
from core.models import Sale, Quotum


def shift_date(d, years, months):
    """Suma `years` años y `months` meses a una fecha, manejando bien el
    "31 de enero + 1 mes = 28/29 de febrero" (ajusta al último día del mes
    destino cuando el día original no existe)."""
    if not d:
        return None
    from calendar import monthrange
    total_months = d.month - 1 + months + years * 12
    new_year = d.year + total_months // 12
    new_month = total_months % 12 + 1
    new_day = min(d.day, monthrange(new_year, new_month)[1])
    return date(new_year, new_month, new_day)


def process_sale(sale_number, years, months, only_pending, confirm):
    sale = Sale.objects.filter(sale_number=sale_number).first()
    if not sale:
        print(f'  ❌ No existe venta con sale_number={sale_number!r}')
        return False

    qs = Quotum.objects.filter(sale=sale, due_date__isnull=False)
    if only_pending:
        qs = qs.exclude(status__in=['paid', 'cancelled'])
    quotas = list(qs.order_by('quota_number'))

    if not quotas:
        print(f'  ({sale_number}) Sin cuotas {"pendientes " if only_pending else ""}para shiftear.')
        return False

    print(f'\n  Venta {sale.sale_number}  (id={sale.id})  fecha venta: {sale.sale_date.date() if sale.sale_date else "?"}')
    print(f'  {len(quotas)} cuota(s) a shiftear ({"sólo pending/overdue" if only_pending else "todas con due_date"})')
    print(f'  Shift: +{years} año(s) +{months} mes(es)')
    print()
    print(f'    {"#":>3}  {"Plan":20}  {"Estado":10}  {"Vieja":12} → {"Nueva":12}')
    print(f'    {"-"*3}  {"-"*20}  {"-"*10}  {"-"*12}   {"-"*12}')

    updates = []  # (quota_id, old_date, new_date)
    for q in quotas:
        old = q.due_date
        new = shift_date(old, years, months)
        if old == new:
            continue
        updates.append((q.id, old, new))
        print(f'    {q.quota_number:>3}  {(q.plan_name or "")[:20]:20}  {q.status:10}  {old}  →  {new}')

    if not updates:
        print('  Nada cambia (shift = 0).')
        return False

    if not confirm:
        print(f'\n  📋 DRY-RUN: {len(updates)} cuota(s) cambiarían su due_date.')
        print('     Para aplicar realmente, repetí el comando con --confirm')
        return False

    # Aplicar.
    with transaction.atomic():
        for qid, _old, new in updates:
            Quotum.objects.filter(id=qid).update(due_date=new)
    print(f'\n  ✓ APLICADO: {len(updates)} cuota(s) actualizadas en venta {sale.sale_number}.')
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('sale_numbers', nargs='+',
                    help='Códigos internos de venta a procesar (ej. MC56/25)')
    p.add_argument('--years', type=int, default=1,
                    help='Cantidad de años a sumar (default 1; usar valor negativo para restar)')
    p.add_argument('--months', type=int, default=0,
                    help='Cantidad de meses a sumar (default 0)')
    p.add_argument('--only-pending', action='store_true',
                    help='Sólo shiftear cuotas que aún no fueron cobradas/canceladas. '
                         'Por default shiftea TODAS las cuotas con due_date (incluso paid), '
                         'porque si la cuota ya está pagada igual conviene tener la fecha '
                         'de vencimiento real para los reportes.')
    p.add_argument('--confirm', action='store_true',
                    help='Confirma escribir a la BD. Sin esta flag es dry-run.')
    args = p.parse_args()

    if args.confirm and connection.vendor == 'postgresql':
        print('\n  ⚠ Conectado a Postgres (probablemente producción).')
        print('     ¿Estás seguro de aplicar el shift en producción?')
        resp = input('     Tipea exactamente "SI APLICAR EN PROD" para continuar: ')
        if resp.strip() != 'SI APLICAR EN PROD':
            print('  Abortado por el usuario.')
            return

    if args.years == 0 and args.months == 0:
        print('  ❌ Shift es cero (--years 0 --months 0). Nada para hacer.')
        return

    total_aplicado = 0
    for sn in args.sale_numbers:
        if process_sale(sn, args.years, args.months, args.only_pending, args.confirm):
            total_aplicado += 1

    if args.confirm:
        print(f'\n  Resumen: {total_aplicado}/{len(args.sale_numbers)} ventas actualizadas.')
    else:
        print(f'\n  (dry-run terminado — no se modificó nada en la BD)')


if __name__ == '__main__':
    main()
