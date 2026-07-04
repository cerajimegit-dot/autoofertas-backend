"""Genera una BD ofuscada para que un Jr trabaje sin acceso a datos sensibles.

QUE OFUSCA:
  Customer:
    first_name        -> CLIENTE{id:04d}
    last_name         -> '' (vacio)
    document_number   -> DOC{id:06d}
    phone, email, address, city, notes -> ''
  Vehicle:
    vin               -> VIN-{id:06d}-{año}
    license_plate     -> ''
    description       -> ''
  Sale:
    notes             -> ''
    (sale_number queda — es codigo de negocio, no personal)
  Quotum:
    notes             -> ''
  CashMovement:
    description       -> regex strip de nombres ej. "Cuota 5/12 venta CM01/24 - JUAN PEREZ" -> "Cuota 5/12 venta CM01/24 - Cliente {customer_id}"
    notes             -> ''
    provider          -> '' (solo para compras al exterior, podria tener datos sensibles)
  AuditLog:
    object_repr       -> redact
    changes           -> regex strip de nombres
  CustomUser:
    first_name, last_name -> ''
    email             -> usuario{id}@local
    password          -> hash de "demo1234" (asi el Jr puede loguearse)

QUE MANTIENE:
  - Todas las FK y relaciones
  - Montos, fechas, status
  - Sale.sale_number (CM01/24, MC42/26 — son codigos de negocio)
  - Brand, VehicleModel (publicos)
  - Branch names (publicos)
  - Enterprise name

GENERA TAMBIEN:
  - db_jr.sqlite3 (BD ofuscada para el Jr)
  - obfuscation_mapping.csv (mapeo original->ofuscado, queda con el senior
    para verificar hallazgos del Jr sin exponer la BD real)

USO:
    DB_ENGINE=sqlite python scripts/obfuscate_db.py
    DB_ENGINE=sqlite python scripts/obfuscate_db.py --output db_jr.sqlite3
"""

import argparse
import csv
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from django.db import connection, transaction
from django.contrib.auth.hashers import make_password
from core.models import (
    Customer, Vehicle, Sale, Quotum, CashMovement, CustomUser,
    AuditLog, Brand, VehicleModel,
)


def strip_proper_nouns(text, customer_id=None):
    """Reemplaza secuencias de palabras en MAYUSCULAS (>=2 chars) por placeholder.

    No es perfecto — puede dejar pasar nombres en minuscula. Pero rocio
    suele escribir nombres en MAYUSCULAS asi que captura la mayoria.
    """
    if not text:
        return text
    # Patron: 2+ palabras consecutivas todas en mayuscula (con ñáéíóú tambien)
    # Reemplaza por "Cliente N" si tenemos customer_id, sino por "[CLIENTE]"
    repl = f'Cliente {customer_id}' if customer_id else '[CLIENTE]'
    cleaned = re.sub(
        r'\b[A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,})+\b',
        repl, text,
    )
    return cleaned


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--output', default='db_jr.sqlite3',
                    help='Archivo destino (default db_jr.sqlite3)')
    p.add_argument('--mapping', default='obfuscation_mapping.csv',
                    help='CSV con mapeo original -> ofuscado (default obfuscation_mapping.csv)')
    p.add_argument('--demo-password', default='demo1234',
                    help='Password para todos los users en la BD ofuscada (default demo1234)')
    args = p.parse_args()

    # 1) Verificar que estamos en SQLite
    if connection.vendor != 'sqlite':
        print(f'  ERROR: este script solo funciona contra SQLite (vendor={connection.vendor})')
        print(f'  Aseguraye DB_ENGINE=sqlite y reintenta.')
        return

    src = connection.settings_dict['NAME']
    print(f'  BD origen: {src}')

    dst = Path(args.output).resolve()
    print(f'  BD destino: {dst}')

    # 2) Copiar archivo
    print(f'  Copiando archivo...')
    shutil.copy2(src, dst)
    print(f'  Copiado: {dst.stat().st_size:,} bytes')

    # 3) Conectar a la copia y modificar
    import sqlite3
    conn = sqlite3.connect(str(dst))
    cur = conn.cursor()

    mapping_rows = []

    # ---- Customer ----
    print('\n  Ofuscando Customer...')
    cur.execute('SELECT id, first_name, last_name, document_number FROM core_customer')
    rows = cur.fetchall()
    for cid, fn, ln, doc in rows:
        new_fn = f'CLIENTE{cid:04d}'
        new_ln = ''
        new_doc = f'DOC{cid:06d}'
        cur.execute(
            'UPDATE core_customer SET first_name=?, last_name=?, document_number=?, '
            'phone=?, email=?, address=?, city=?, notes=? WHERE id=?',
            (new_fn, new_ln, new_doc, '', '', '', '', '', cid),
        )
        mapping_rows.append({
            'table': 'customer', 'id': cid,
            'original': f'{fn} {ln} ({doc})',
            'obfuscated': f'{new_fn} ({new_doc})',
        })
    print(f'    {len(rows)} clientes ofuscados')

    # ---- Vehicle ----
    print('  Ofuscando Vehicle...')
    cur.execute('SELECT id, vin, year FROM core_vehicle')
    rows = cur.fetchall()
    for vid, vin, year in rows:
        new_vin = f'VIN-{vid:06d}-{year or 2000}'
        cur.execute(
            'UPDATE core_vehicle SET vin=?, license_plate=?, description=? WHERE id=?',
            (new_vin, '', '', vid),
        )
        mapping_rows.append({
            'table': 'vehicle', 'id': vid,
            'original': vin or '',
            'obfuscated': new_vin,
        })
    print(f'    {len(rows)} vehiculos ofuscados')

    # ---- Sale ----
    print('  Ofuscando Sale.notes...')
    cur.execute('UPDATE core_sale SET notes=? WHERE notes IS NOT NULL AND notes != ?', ('', ''))
    print(f'    {cur.rowcount} notas de venta limpiadas')

    # ---- Quotum ----
    print('  Ofuscando Quotum.notes...')
    cur.execute('UPDATE core_quotum SET notes=? WHERE notes IS NOT NULL AND notes != ?', ('', ''))
    print(f'    {cur.rowcount} notas de cuota limpiadas')

    # ---- CashMovement (description tiene nombres embebidos) ----
    print('  Ofuscando CashMovement.description y .provider y .notes...')
    cur.execute('SELECT id, description FROM core_cashmovement')
    rows = cur.fetchall()
    n_cleaned = 0
    for cmid, desc in rows:
        new_desc = strip_proper_nouns(desc or '', customer_id=None)
        if new_desc != (desc or ''):
            n_cleaned += 1
        cur.execute(
            'UPDATE core_cashmovement SET description=?, provider=?, notes=? WHERE id=?',
            (new_desc, '', '', cmid),
        )
    print(f'    {len(rows)} CashMovements procesados ({n_cleaned} tenian nombres)')

    # ---- AuditLog ----
    print('  Ofuscando AuditLog...')
    try:
        cur.execute('SELECT id, object_repr, changes FROM core_auditlog')
        rows = cur.fetchall()
        for aid, repr_, changes in rows:
            new_repr = strip_proper_nouns(repr_ or '')
            new_changes = strip_proper_nouns(changes or '')
            cur.execute(
                'UPDATE core_auditlog SET object_repr=?, changes=? WHERE id=?',
                (new_repr, new_changes, aid),
            )
        print(f'    {len(rows)} audit logs limpiados')
    except sqlite3.OperationalError as e:
        print(f'    (saltada: {e})')

    # ---- CustomUser ----
    print('  Ofuscando CustomUser...')
    new_password = make_password(args.demo_password)
    cur.execute('SELECT id, username FROM core_customuser')
    rows = cur.fetchall()
    for uid, username in rows:
        new_email = f'usuario{uid}@local'
        cur.execute(
            'UPDATE core_customuser SET first_name=?, last_name=?, email=?, password=? WHERE id=?',
            ('', '', new_email, new_password, uid),
        )
        mapping_rows.append({
            'table': 'user', 'id': uid,
            'original': username,
            'obfuscated': f'pass={args.demo_password}',
        })
    print(f'    {len(rows)} usuarios ofuscados (password ahora: {args.demo_password})')

    conn.commit()
    conn.close()

    # 4) Escribir mapping CSV (queda con el senior)
    mapping_path = Path(args.mapping).resolve()
    with open(mapping_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, delimiter=';',
                           fieldnames=['table', 'id', 'original', 'obfuscated'])
        w.writeheader()
        w.writerows(mapping_rows)
    print(f'\n  Mapping guardado: {mapping_path}')
    print(f'  GUARDA ESTE ARCHIVO — necesario para des-ofuscar hallazgos del Jr.')
    print(f'  NO se lo pases al Jr.')

    print(f'\n  LISTO. Archivos:')
    print(f'    BD ofuscada para Jr:  {dst}')
    print(f'    Mapping (senior):     {mapping_path}')
    print(f'\n  Para que el Jr la use, pasale solo {dst.name}.')
    print(f'  Login en la copia: cualquier usuario con password = {args.demo_password}')


if __name__ == '__main__':
    main()
