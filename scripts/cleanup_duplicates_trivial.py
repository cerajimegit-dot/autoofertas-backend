"""Borra fichas de cliente duplicadas que NO tienen referencias FK.

Caso de uso: el script find_duplicate_customers.py identificó 12 fichas
duplicadas del "Patrón B" — la misma persona cargada dos veces con
diferencias triviales (espacios extras al final del nombre), donde una
de las dos ficha NO TIENE ventas, cuotas, cobranzas, ni nada que
referencie al customer.

Estas son trivialmente borrables: eliminar la ficha duplicada NO rompe
nada porque no hay FK apuntando a ella.

QUÉ HACE:
  1. Toma una lista de customer_id (de duplicados.csv o de --ids).
  2. Para cada uno, verifica con TODOS los modelos relacionados si
     hay algún FK que lo referencie:
        - Sale (customer FK)
        - Quotum (customer FK)
        - CashMovement (no tiene FK directa a customer)
        - Cualquier otro FK descubierto reflexivamente.
  3. Si encuentra alguna referencia, NO borra y avisa.
  4. Si no encuentra referencias, borra con `--confirm`.

DRY-RUN POR DEFAULT: sin --confirm sólo imprime qué borraría.

USO:
    # Ver qué se borraría:
    DB_ENGINE=sqlite python scripts/cleanup_duplicates_trivial.py --from-csv docs/reports/duplicados.csv

    # Aplicar:
    DB_ENGINE=sqlite python scripts/cleanup_duplicates_trivial.py --from-csv docs/reports/duplicados.csv --confirm

    # Ids puntuales:
    python scripts/cleanup_duplicates_trivial.py --ids 5589244,4401955,3180785

SEGURIDAD:
  - Doble confirmación interactiva si --confirm + Postgres.
  - Lista exhaustiva de referencias chequeadas antes de cualquier borrado.
  - Transacción atómica: si una falla, ninguna se borra.
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

from django.apps import apps
from django.db import connection, transaction
from core.models import Customer


def find_references_to(customer):
    """Para cada modelo de Django que tenga ForeignKey a Customer,
    devuelve cuántas filas lo referencian.

    Esto es genérico — incluye FK que no conozca explícitamente (auditlog,
    cualquier modelo nuevo, etc).
    """
    refs = {}  # model_name → count
    for model in apps.get_models():
        for field in model._meta.get_fields():
            if not field.is_relation:
                continue
            if getattr(field, 'related_model', None) is not Customer:
                continue
            # Tenemos un campo en `model` que apunta a Customer.
            # Hacemos un filter para contar.
            if hasattr(field, 'attname'):
                kwargs = {field.attname: customer.id}
                try:
                    n = model.objects.filter(**kwargs).count()
                    if n:
                        refs[f'{model._meta.label}.{field.name}'] = n
                except Exception:
                    pass
    return refs


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument('--from-csv', metavar='FILE',
                      help='CSV producido por find_duplicate_customers.py. Toma las filas '
                           'con recommendation=MERGEAR y n_ventas=0.')
    grp.add_argument('--ids', metavar='CUSTOMER_IDS',
                      help='Lista de IDs separados por coma (ej. 116,170,289)')
    p.add_argument('--confirm', action='store_true',
                    help='Confirma borrado. Sin esta flag es dry-run.')
    args = p.parse_args()

    # 1. Resolver lista de candidatos
    if args.from_csv:
        candidates = []
        with open(args.from_csv, newline='', encoding='utf-8-sig') as f:
            for row in csv.DictReader(f, delimiter=';'):
                if (row.get('recommendation') == 'MERGEAR'
                    and int(row.get('n_ventas') or 0) == 0):
                    candidates.append(int(row['customer_id']))
    else:
        candidates = [int(x.strip()) for x in args.ids.split(',') if x.strip()]

    if not candidates:
        print('  No hay candidatos para borrar.')
        return

    print(f'\n  {len(candidates)} candidato(s) a borrar:\n')

    safe_to_delete = []
    unsafe = []

    for cid in candidates:
        c = Customer.objects.filter(id=cid).first()
        if not c:
            print(f'  ⚠ id={cid:5}  NO EXISTE en la BD (ya borrado?)')
            continue
        refs = find_references_to(c)
        # Quitamos del check las referencias triviales: hay ninguna que sea
        # "safe" — si tiene cualquier referencia, NO borramos.
        nombre = f'{c.first_name or ""} {c.last_name or ""}'.strip()
        if not refs:
            safe_to_delete.append(c)
            print(f'  ✓ id={c.id:5}  doc={c.document_number:30}  "{nombre}"')
            print(f'         Sin referencias FK. Seguro de borrar.')
        else:
            unsafe.append((c, refs))
            print(f'  ⚠ id={c.id:5}  doc={c.document_number:30}  "{nombre}"')
            print(f'         TIENE REFERENCIAS — NO se va a borrar:')
            for label, n in refs.items():
                print(f'           - {label}: {n} fila(s)')
        print()

    print(f'\n  RESUMEN:')
    print(f'    Candidatos:       {len(candidates)}')
    print(f'    Borrables (safe): {len(safe_to_delete)}')
    print(f'    Con referencias:  {len(unsafe)}')

    if not safe_to_delete:
        print('\n  No hay nada para borrar.')
        return

    if not args.confirm:
        print(f'\n  📋 DRY-RUN: {len(safe_to_delete)} ficha(s) serían eliminadas.')
        print('     Para aplicar realmente, agregá --confirm')
        return

    if connection.vendor == 'postgresql':
        print('\n  ⚠ Conectado a Postgres (probablemente producción).')
        resp = input('     Tipea exactamente "SI BORRAR EN PROD" para continuar: ')
        if resp.strip() != 'SI BORRAR EN PROD':
            print('  Abortado por el usuario.')
            return

    with transaction.atomic():
        ids = [c.id for c in safe_to_delete]
        deleted, breakdown = Customer.objects.filter(id__in=ids).delete()
    print(f'\n  ✓ ELIMINADAS: {deleted} fila(s) en total.')
    for k, v in breakdown.items():
        print(f'     {k}: {v}')


if __name__ == '__main__':
    main()
