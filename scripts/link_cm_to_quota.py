"""Linkea un CashMovement a una Quotum especifica (setea quota_id).

Hace validaciones de seguridad antes de aplicar:
  - Verifica que el CashMovement existe y no tiene quota_id ya seteado
  - Verifica que la Quotum existe
  - Si amounts difieren > 5%, pide --force
  - Si fechas difieren > 60 dias, pide --force

USO:
    DB_ENGINE=sqlite python scripts/link_cm_to_quota.py CM_ID QUOTA_ID
    DB_ENGINE=sqlite python scripts/link_cm_to_quota.py 42 155 --confirm
    DB_ENGINE=sqlite python scripts/link_cm_to_quota.py 42 155 --confirm --force
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from django.db import connection, transaction
from core.models import CashMovement, Quotum


def fmt(n):
    return f'Gs.{int(n or 0):,}'.replace(',', '.')


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('cm_id', type=int)
    p.add_argument('quota_id', type=int)
    p.add_argument('--confirm', action='store_true')
    p.add_argument('--force', action='store_true',
                    help='Aplicar aunque haya warnings de amount/fecha')
    args = p.parse_args()

    cm = CashMovement.objects.filter(id=args.cm_id).select_related('sale').first()
    if not cm:
        print(f'  No existe CashMovement id={args.cm_id}')
        return

    q = Quotum.objects.filter(id=args.quota_id).select_related('sale').first()
    if not q:
        print(f'  No existe Quotum id={args.quota_id}')
        return

    print(f'\n  CashMovement #{cm.id}:')
    print(f'    fecha={cm.date}  monto={fmt(cm.amount)}  kind={cm.kind}')
    print(f'    sale_id={cm.sale_id}  sale_number={cm.sale.sale_number if cm.sale else "—"}')
    print(f'    quota_id actual: {cm.quota_id or "(NULL)"}')

    print(f'\n  Quotum #{q.id}:')
    print(f'    sale_id={q.sale_id}  sale_number={q.sale.sale_number if q.sale else "—"}')
    print(f'    quota_number={q.quota_number}/{q.total_plan}  amount={fmt(q.amount)}')
    print(f'    due_date={q.due_date}  payment_date={q.payment_date}  status={q.status}')

    warnings = []

    if cm.quota_id and cm.quota_id != q.id:
        print(f'\n  ❌ El CashMovement ya tiene quota_id={cm.quota_id} (distinto al pedido).')
        print(f'     No se sobreescribe. Si querés reasignar, primero NULLEA con:')
        print(f'     >>> CashMovement.objects.filter(id={cm.id}).update(quota_id=None)')
        return

    amount_diff_pct = abs(int(cm.amount or 0) - int(q.amount or 0)) / max(int(cm.amount or 1), 1) * 100
    if amount_diff_pct > 5:
        warnings.append(f'⚠ Amount difiere {amount_diff_pct:.1f}% (CM={fmt(cm.amount)}, Q={fmt(q.amount)})')

    if cm.date and q.due_date:
        days = abs((cm.date - q.due_date).days)
        if days > 60:
            warnings.append(f'⚠ Fecha CM vs due_date de Q: {days} dias de diferencia')

    if cm.sale_id and q.sale_id and cm.sale_id != q.sale_id:
        warnings.append(f'⚠ sale_id distinto: CM={cm.sale_id}, Q={q.sale_id} — esto es muy raro')

    if warnings:
        print('\n  Advertencias:')
        for w in warnings:
            print(f'    {w}')
        if not args.force:
            print(f'\n  Hay warnings. Para aplicar de todos modos, agregar --force')
            return

    if not args.confirm:
        print(f'\n  DRY-RUN. Para aplicar:')
        print(f'    python scripts/link_cm_to_quota.py {cm.id} {q.id} --confirm{" --force" if warnings else ""}')
        return

    if connection.vendor == 'postgresql':
        resp = input('  Tipea "SI APLICAR EN PROD": ')
        if resp.strip() != 'SI APLICAR EN PROD':
            return

    with transaction.atomic():
        CashMovement.objects.filter(id=cm.id).update(quota_id=q.id)
        # Si la quota no estaba paid y el CM es cobro_cuota, tal vez tambien
        # deba marcar la quota como paid. NO lo hacemos aca — el Jr debe
        # decidir explicitamente.

    print(f'\n  ✓ APLICADO: CashMovement #{cm.id}.quota_id = {q.id}')


if __name__ == '__main__':
    main()
