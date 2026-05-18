"""Consulta las cuotas de una venta por su `sale_number`.

Funciona contra SQLite local (DB_ENGINE=sqlite) o Postgres / Supabase
(DB_ENGINE=postgres). Read-only: no toca la base, sólo imprime.

Útil para verificar antes de aplicar un fix masivo (ej. shift de año).

USO:
    DB_ENGINE=sqlite python scripts/inspect_sale_quotas.py MC56/25
    DB_ENGINE=postgres python scripts/inspect_sale_quotas.py MC56/25
    python scripts/inspect_sale_quotas.py MC56/25 MC57/25 CM12/26   # varias

Opcionalmente con `--json` imprime en JSON para piping.
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Sale, Quotum


def fmt_money(n):
    return f'Gs. {int(n or 0):,}'.replace(',', '.')


def report(sale_number, as_json=False):
    sale = Sale.objects.filter(sale_number=sale_number).select_related(
        'customer', 'vehicle', 'vehicle__brand', 'vehicle__model',
        'branch', 'payment_form', 'enterprise',
    ).first()

    if not sale:
        msg = {'sale_number': sale_number, 'error': 'No existe en la BD'}
        if as_json:
            print(json.dumps(msg, ensure_ascii=False, indent=2))
        else:
            print(f'\n  ❌ No existe venta con sale_number={sale_number!r}')
        return

    quotas = list(Quotum.objects.filter(sale=sale).order_by('quota_number'))

    if as_json:
        out = {
            'sale': {
                'id': sale.id,
                'sale_number': sale.sale_number,
                'enterprise': sale.enterprise.name if sale.enterprise_id else None,
                'sale_date': sale.sale_date.isoformat() if sale.sale_date else None,
                'status': sale.status,
                'customer': str(sale.customer) if sale.customer_id else None,
                'vehicle': str(sale.vehicle) if sale.vehicle_id else None,
                'branch': sale.branch.name if sale.branch_id else None,
                'total_price': float(sale.total_price or 0),
                'down_payment': float(sale.down_payment or 0),
                'payment_form': sale.payment_form.name if sale.payment_form_id else None,
            },
            'quotas': [
                {
                    'id': q.id,
                    'quota_number': q.quota_number,
                    'total_plan': q.total_plan,
                    'plan_name': q.plan_name,
                    'amount': float(q.amount or 0),
                    'due_date': q.due_date.isoformat() if q.due_date else None,
                    'status': q.status,
                    'payment_date': q.payment_date.isoformat() if q.payment_date else None,
                    'payment_method': q.payment_method,
                } for q in quotas
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    # Reporte legible
    today = date.today()
    print(f'\n{"=" * 78}')
    print(f'  Venta: {sale.sale_number}    ID interno: {sale.id}')
    print(f'{"=" * 78}')
    print(f'  Empresa:        {sale.enterprise.name if sale.enterprise_id else "(sin empresa)"}')
    print(f'  Sucursal:       {sale.branch.name if sale.branch_id else "(sin sucursal)"}')
    print(f'  Fecha de venta: {sale.sale_date}')
    print(f'  Estado:         {sale.status} ({sale.get_status_display()})')
    print(f'  Cliente:        {sale.customer}' if sale.customer_id else '  Cliente:        (sin cliente)')
    print(f'  Vehículo:       {sale.vehicle}' if sale.vehicle_id else '  Vehículo:       (sin vehículo)')
    print(f'  Forma de pago:  {sale.payment_form.name if sale.payment_form_id else "-"}')
    print(f'  Precio total:   {fmt_money(sale.total_price)}')
    if sale.down_payment:
        print(f'  Entrega inicial:{fmt_money(sale.down_payment)}')
        print(f'  A financiar:    {fmt_money((sale.total_price or 0) - (sale.down_payment or 0))}')

    print(f'\n  Cuotas: {len(quotas)}')
    if not quotas:
        print('  (No tiene cuotas generadas.)')
        return

    total = sum(float(q.amount or 0) for q in quotas)
    cobradas = sum(float(q.amount or 0) for q in quotas if q.status == 'paid')
    print(f'  Total plan:     {fmt_money(total)}   Cobrado: {fmt_money(cobradas)}')
    print()
    print(f'    {"#":>3}  {"Plan":20}  {"Monto":>14}  {"Vence":12}  {"Estado":10}  {"Días":>6}  Pago')
    print(f'    {"-"*3}  {"-"*20}  {"-"*14}  {"-"*12}  {"-"*10}  {"-"*6}  {"-"*12}')
    for q in quotas:
        if q.due_date:
            dias = (q.due_date - today).days
            dias_str = f'{dias:+d}' if dias else '0'
        else:
            dias_str = '-'
        pago = q.payment_date.isoformat() if q.payment_date else '-'
        marca = '⚠' if (q.due_date and q.due_date < today and q.status != 'paid' and q.status != 'cancelled') else ' '
        print(f'  {marca} {q.quota_number:>3}  {(q.plan_name or "")[:20]:20}  {fmt_money(q.amount):>14}  '
              f'{str(q.due_date) if q.due_date else "-":12}  {q.status:10}  {dias_str:>6}  {pago}')


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('sale_numbers', nargs='+',
                    help='Códigos internos de venta a consultar (ej. MC56/25 CM12/26)')
    p.add_argument('--json', action='store_true',
                    help='Salida en JSON en vez de tabla legible')
    args = p.parse_args()
    for sn in args.sale_numbers:
        report(sn, as_json=args.json)


if __name__ == '__main__':
    main()
