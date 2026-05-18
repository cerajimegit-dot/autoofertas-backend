"""Borra cuotas asociadas a la venta placeholder VDUMMY (o similar).

CONTEXTO:
La migración del sistema viejo creó una "venta placeholder" con
sale_number='VDUMMY' (cliente "Dummy Cuotas", vehículo "DUMMY") para
poder colgar cuotas históricas que no tenían venta asociada en la
planilla Excel original.

Resultado: hay 54 cuotas que apuntan a esta venta. Cada una corresponde
a un cliente con doc autogenerado (CUOTA000170, CUOTA000175, etc.) y
representa una "deuda histórica" sin contrato real.

Estas cuotas inflan la cartera vencida en ~Gs. 1.091.000.000 sin
representar nada cobrable — son ruido importado de la planilla vieja.

QUÉ HACE:
  1. Busca todas las cuotas con sale__sale_number=='VDUMMY' (o lo que
     se pase con --sale-number).
  2. Verifica que NINGUNA tenga payment_date (no perdemos historial).
  3. Verifica que no haya CashMovements vinculados (no hay).
  4. Lista todo con detalles antes de borrar.
  5. Dry-run por default; --confirm para aplicar.

DESPUÉS:
Los clientes CUOTA000XXX quedan sin cuotas y sin ventas → pasan a ser
trivialmente borrables con scripts/cleanup_duplicates_trivial.py --ids.
El script reporta los IDs al final para facilitar el siguiente paso.

USO:
    # Dry-run (default):
    DB_ENGINE=sqlite python scripts/cleanup_dummy_quotas.py

    # Aplicar:
    DB_ENGINE=sqlite python scripts/cleanup_dummy_quotas.py --confirm

    # Otra venta placeholder:
    python scripts/cleanup_dummy_quotas.py --sale-number OTRO_DUMMY --confirm

SEGURIDAD:
  - Aborta si encuentra cuotas paid con payment_date (no esperado).
  - Doble confirmación interactiva en Postgres.
  - Transacción atómica.
"""

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from django.db import connection, transaction
from django.db.models import Sum
from core.models import Sale, Quotum, CashMovement


def fmt(n):
    return f'Gs. {int(n or 0):,}'.replace(',', '.')


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--sale-number', default='VDUMMY',
                    help='Sale number cuyas cuotas se quieren borrar (default VDUMMY).')
    p.add_argument('--confirm', action='store_true',
                    help='Confirma el borrado. Sin esto es dry-run.')
    args = p.parse_args()

    sale = Sale.objects.filter(sale_number=args.sale_number).first()
    if not sale:
        print(f'  ❌ No existe la venta con sale_number={args.sale_number!r}')
        return

    quotas = Quotum.objects.filter(sale=sale).select_related('customer')
    n = quotas.count()
    monto = quotas.aggregate(s=Sum('amount'))['s'] or 0

    print(f'\n  Venta placeholder: "{sale.sale_number}" (id={sale.id})')
    print(f'    Cliente:   {sale.customer}')
    print(f'    Vehículo:  {sale.vehicle}')
    print(f'    Status:    {sale.status}')
    print(f'    Total:     {fmt(sale.total_price)}')
    print()
    print(f'  Cuotas que apuntan a esta venta: {n}')
    print(f'    Monto total:    {fmt(monto)}')

    if n == 0:
        print('  Nada para borrar.')
        return

    # Validación de seguridad: ninguna debe tener payment_date
    pagadas = quotas.exclude(payment_date__isnull=True)
    if pagadas.exists():
        print(f'\n  ⚠ ATENCIÓN: hay {pagadas.count()} cuota(s) con payment_date '
              f'(o sea, ya cobradas). Eso sí sería historial real.')
        print('     Aborto. Revisar manualmente cuáles antes de continuar.')
        for q in pagadas[:10]:
            print(f'       id={q.id} cliente={q.customer.full_name if q.customer_id else "?"} pagada {q.payment_date} Gs.{int(q.amount):,}'.replace(',', '.'))
        return

    # CashMovements vinculados?
    qids = list(quotas.values_list('id', flat=True))
    cms = CashMovement.objects.filter(quota_id__in=qids)
    if cms.exists():
        print(f'\n  ⚠ ATENCIÓN: hay {cms.count()} CashMovement(s) vinculados a estas cuotas.')
        print('     Borrar las cuotas dejaría esos movimientos huérfanos (quota_id NULL).')
        print('     Aborto. Revisar manualmente.')
        return

    # Resumen por cliente
    print()
    print('  Distribución por cliente:')
    customers_seen = set()
    by_cust = defaultdict(lambda: {'n': 0, 'total': 0, 'name': '', 'doc': ''})
    for q in quotas:
        c = q.customer
        if not c:
            continue
        customers_seen.add(c.id)
        by_cust[c.id]['n'] += 1
        by_cust[c.id]['total'] += float(q.amount or 0)
        by_cust[c.id]['name'] = c.full_name
        by_cust[c.id]['doc'] = c.document_number or ''
    print(f'    Clientes únicos referenciados: {len(customers_seen)}')
    print()
    for cid, info in sorted(by_cust.items(), key=lambda x: -x[1]['total'])[:10]:
        print(f'    id={cid:5}  {info["doc"]:18}  {info["name"]:30}  {info["n"]:>2} cuota(s)  {fmt(info["total"])}')
    if len(by_cust) > 10:
        print(f'    ... y {len(by_cust)-10} cliente(s) más')

    if not args.confirm:
        print(f'\n  📋 DRY-RUN: se borrarían {n} cuota(s) por {fmt(monto)}.')
        print()
        print('  Para aplicar realmente, agregá --confirm')
        print()
        print('  Después de aplicar, podés borrar los clientes CUOTA000XXX que queden')
        print(f'  sin referencias con:')
        ids_csv = ','.join(str(cid) for cid in sorted(customers_seen))
        print(f'    python scripts/cleanup_duplicates_trivial.py --ids {ids_csv}')
        return

    if connection.vendor == 'postgresql':
        print('\n  ⚠ Conectado a Postgres (probablemente producción).')
        resp = input('     Tipea exactamente "SI BORRAR CUOTAS DUMMY" para continuar: ')
        if resp.strip() != 'SI BORRAR CUOTAS DUMMY':
            print('  Abortado por el usuario.')
            return

    with transaction.atomic():
        deleted, breakdown = Quotum.objects.filter(id__in=qids).delete()
    print(f'\n  ✓ ELIMINADAS: {deleted} fila(s) en total.')
    for k, v in breakdown.items():
        print(f'     {k}: {v}')

    print()
    print(f'  Los siguientes {len(customers_seen)} clientes ya no tienen cuotas asociadas.')
    print('  Probablemente ahora son borrables con:')
    ids_csv = ','.join(str(cid) for cid in sorted(customers_seen))
    print(f'    python scripts/cleanup_duplicates_trivial.py --ids {ids_csv} --confirm')


if __name__ == '__main__':
    main()
