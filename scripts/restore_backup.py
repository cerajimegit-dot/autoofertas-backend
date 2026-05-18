#!/usr/bin/env python
"""
Restore de un snapshot de la BD a Supabase (o a una BD local de testing).

USO:
    # Restore en local de testing (sin pisar producción):
    DB_ENGINE=sqlite python scripts/restore_backup.py backups/snapshot_xxx.json.gz

    # Restore en producción Supabase (¡con cuidado!):
    python scripts/restore_backup.py backups/snapshot_xxx.json.gz --confirm-prod

OPCIONES:
    --confirm-prod          Necesario para restaurar contra Supabase prod.
    --truncate              Vacía las tablas antes de cargar (pierde datos).
    --tables a,b,c          Restaura sólo esas tablas (ej: core.sale,core.quotum).
    --dry-run               Lee el archivo y valida sin tocar la BD.

QUÉ HACE:
    1. Descomprime el .gz si hace falta.
    2. Valida que el JSON tenga estructura de Django dumpdata.
    3. Muestra resumen (qué tablas, cuántas filas) antes de tocar nada.
    4. Pide confirmación explícita si va contra Supabase prod.
    5. Llama a `manage.py loaddata` que respeta FKs y unique constraints.

QUÉ NO HACE:
    - NO borra datos por default. Si querés restore limpio, --truncate.
    - NO mueve secuencias (auto-incrementos) en Postgres. Si después de
      restore te tira "duplicate key", correr ALTER SEQUENCE ... RESTART
      (ver README).
    - NO restaura token_blacklist (los tokens viejos no sirven).
"""
import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('backup_file', help='Ruta al archivo .json o .json.gz')
    parser.add_argument('--confirm-prod', action='store_true',
                        help='Confirmá que querés restaurar contra Supabase producción')
    parser.add_argument('--truncate', action='store_true',
                        help='Vaciar las tablas antes de cargar (¡pierde datos actuales!)')
    parser.add_argument('--tables', default=None,
                        help='Lista de tablas (coma) — restaurar sólo esas. Ej: core.sale,core.quotum')
    parser.add_argument('--dry-run', action='store_true',
                        help='Sólo validar el archivo, no escribir nada')
    args = parser.parse_args()

    backup = Path(args.backup_file)
    if not backup.exists():
        sys.exit(f'ERROR: {backup} no existe.')

    # --------- Validar contexto ---------
    db_engine = os.environ.get('DB_ENGINE', 'sqlite')
    is_prod = (db_engine == 'postgres')

    print('=' * 60)
    print(f'Backup file:     {backup}')
    print(f'Tamaño:          {backup.stat().st_size:,} bytes')
    print(f'DB_ENGINE:       {db_engine}  →  {"⚠ PRODUCCIÓN" if is_prod else "local (seguro)"}')
    print(f'Modo:            {"DRY-RUN" if args.dry_run else ("TRUNCATE + LOAD" if args.truncate else "LOAD (merge)")}')
    print('=' * 60)

    if is_prod and not args.confirm_prod and not args.dry_run:
        sys.exit(
            'ABORT: estás apuntando a Supabase producción y no pasaste --confirm-prod.\n'
            '       Por seguridad, requerimos confirmación explícita.\n'
            '       Si querés restaurar a una BD local primero (recomendado), corré:\n'
            '         DB_ENGINE=sqlite python scripts/restore_backup.py ' + str(backup)
        )

    # --------- Descomprimir si hace falta ---------
    if backup.suffix == '.gz':
        tmpdir = tempfile.mkdtemp()
        unc = Path(tmpdir) / backup.stem
        print(f'Descomprimiendo a {unc}...')
        with gzip.open(backup, 'rb') as fin, open(unc, 'wb') as fout:
            shutil.copyfileobj(fin, fout)
        json_file = unc
    else:
        json_file = backup

    # --------- Validar JSON ---------
    print('Validando JSON...')
    with open(json_file, encoding='utf-8') as f:
        data = json.load(f)

    from collections import Counter
    counts = Counter(r['model'] for r in data)
    print(f'\nResumen del backup:')
    for model, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f'   {model:30s} {n:6d}')
    print(f'   {"TOTAL":30s} {len(data):6d} filas')
    print()

    # --------- Filtrar tablas si --tables ---------
    if args.tables:
        wanted = set(args.tables.split(','))
        filtered = [r for r in data if r['model'] in wanted]
        print(f'Filtro --tables: {len(data)} → {len(filtered)} filas')
        # Escribir a un JSON nuevo
        filtered_path = json_file.with_suffix('.filtered.json')
        with open(filtered_path, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)
        json_file = filtered_path

    if args.dry_run:
        print('\n✓ Dry-run OK. Archivo válido, no se escribió nada.')
        return

    # --------- Confirmación interactiva en prod ---------
    if is_prod:
        print()
        print('⚠  ESTÁS A PUNTO DE ESCRIBIR EN SUPABASE PRODUCCIÓN.')
        confirm = input('   Escribí "SI RESTAURAR" para continuar: ').strip()
        if confirm != 'SI RESTAURAR':
            sys.exit('Abortado.')

    # --------- Truncate (opcional) ---------
    if args.truncate:
        if not is_prod or args.confirm_prod:
            print('Truncando tablas antes de cargar...')
            confirm = input('   Esto borra TODO antes de restaurar. Escribí "SI BORRAR": ').strip()
            if confirm != 'SI BORRAR':
                sys.exit('Abortado.')
            # Truncate tablas en orden inverso de dependencias
            run_django_shell(
                "from core.models import CashMovement, Quotum, Sale, VehicleCost, "
                "Vehicle, VehicleModel, Brand, ExchangeRate, Customer, PaymentForm, "
                "AuditLog, ViewPermission, CustomUser, Branch, Enterprise; "
                "[m.objects.all().delete() for m in ("
                "CashMovement, Quotum, Sale, VehicleCost, Vehicle, VehicleModel, "
                "Brand, ExchangeRate, Customer, PaymentForm, AuditLog, ViewPermission)]"
            )

    # --------- Cargar con loaddata ---------
    print(f'Cargando {json_file}...')
    cmd = ['python', 'manage.py', 'loaddata', str(json_file)]
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    if result.returncode != 0:
        sys.exit('ERROR: loaddata falló. Revisar output arriba.')

    print()
    print('✓ Restore completado.')
    if is_prod:
        print()
        print('PRÓXIMO PASO recomendado: resetear las secuencias de Postgres')
        print('para evitar errores "duplicate key value" en próximas inserciones.')
        print('Correr:')
        print('   python scripts/restore_backup.py --reset-sequences')


def run_django_shell(code: str) -> None:
    """Ejecuta código Python en el shell de Django."""
    cmd = ['python', 'manage.py', 'shell', '-c', code]
    subprocess.run(cmd, cwd=Path(__file__).parent.parent, check=True)


if __name__ == '__main__':
    main()
