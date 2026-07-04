"""Lista CashMovements de tipo 'cobro_cuota' que no tienen quota_id linkeado.

Estos son los que el Jr debe revisar uno por uno y vincular a la
Quotum correcta.

Categorias del output:
  1. CM con sale_id set pero quota_id NULL  (mas faciles — sabemos la venta)
  2. CM sin sale_id ni quota_id  (mas dificiles — solo description y monto)

USO:
    DB_ENGINE=sqlite python scripts/find_unlinked_cobros.py
    DB_ENGINE=sqlite python scripts/find_unlinked_cobros.py --csv docs/reports/cm_unlinked.csv
"""

import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import CashMovement


def fmt(n):
    return f'Gs.{int(n or 0):,}'.replace(',', '.')


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--csv', metavar='FILE')
    args = p.parse_args()

    qs = CashMovement.objects.filter(
        kind='cobro_cuota',
        quota__isnull=True,
    ).select_related('sale', 'sale__customer').order_by('date', 'id')

    with_sale = qs.filter(sale__isnull=False)
    without_sale = qs.filter(sale__isnull=True)

    print(f'\n  Total CashMovements cobro_cuota sin link a Quotum: {qs.count()}')
    print(f'    Con sale_id (mas facil): {with_sale.count()}')
    print(f'    Sin sale_id (mas dificil): {without_sale.count()}')

    print(f'\n  === CON sale_id (top 50) ===')
    print(f'  {"id":>5}  {"fecha":12}  {"monto":>14}  {"sale_id":>7}  {"sale_number":15}  description')
    for cm in with_sale[:50]:
        sn = cm.sale.sale_number if cm.sale else ''
        print(f'  {cm.id:>5}  {str(cm.date):12}  {fmt(cm.amount):>14}  {cm.sale_id or "":>7}  {sn:15}  {(cm.description or "")[:70]}')
    if with_sale.count() > 50:
        print(f'  ... y {with_sale.count() - 50} mas')

    print(f'\n  === SIN sale_id (top 30) ===')
    print(f'  {"id":>5}  {"fecha":12}  {"monto":>14}  description')
    for cm in without_sale[:30]:
        print(f'  {cm.id:>5}  {str(cm.date):12}  {fmt(cm.amount):>14}  {(cm.description or "")[:80]}')
    if without_sale.count() > 30:
        print(f'  ... y {without_sale.count() - 30} mas')

    if args.csv:
        out = Path(args.csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(['cm_id', 'date', 'amount', 'sale_id', 'sale_number',
                        'description', 'category'])
            for cm in qs:
                w.writerow([
                    cm.id, cm.date, int(cm.amount or 0),
                    cm.sale_id or '',
                    cm.sale.sale_number if cm.sale else '',
                    cm.description or '',
                    'con_sale' if cm.sale_id else 'sin_sale',
                ])
        print(f'\n  CSV guardado: {out.resolve()}')


if __name__ == '__main__':
    main()
