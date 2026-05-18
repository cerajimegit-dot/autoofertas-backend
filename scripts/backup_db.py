#!/usr/bin/env python
"""
Genera un snapshot completo de la BD a backups/snapshot_TS.json.gz.

USO:
    python scripts/backup_db.py
    python scripts/backup_db.py --output backups/manual.json
    python scripts/backup_db.py --keep-last 30   # borra backups viejos

QUÉ HACE:
  1. Corre `manage.py dumpdata core` con natural keys (portable).
  2. Comprime con gzip (~25× reducción).
  3. Calcula hash MD5 para verificación.
  4. (Opcional) Borra backups más viejos que --keep-last.

NO REQUIERE pg_dump ni acceso directo a Postgres — funciona contra
el transaction pooler de Supabase (cualquier conexión Django sirve).
"""
import argparse
import gzip
import hashlib
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKUPS = ROOT / 'backups'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', default=None,
                        help='Ruta del archivo. Por default: backups/snapshot_<TS>.json')
    parser.add_argument('--no-compress', action='store_true', help='No comprimir con gzip')
    parser.add_argument('--keep-last', type=int, default=None,
                        help='Borrar backups más viejos que los últimos N')
    args = parser.parse_args()

    BACKUPS.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    out = Path(args.output) if args.output else BACKUPS / f'snapshot_{ts}.json'

    print(f'=== Generando backup → {out} ===')
    t0 = time.time()
    cmd = [
        sys.executable, 'manage.py', 'dumpdata', 'core',
        '--natural-primary', '--natural-foreign',
        '--indent', '2',
        '--output', str(out),
    ]
    # En Windows, Python por default escribe el archivo con encoding del
    # sistema (cp1252). Forzamos UTF-8 para que el JSON sea portable y
    # parseable desde cualquier OS (incluido el runner de GitHub Actions).
    env = os.environ.copy()
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    if result.returncode != 0:
        sys.exit('ERROR: dumpdata falló.')

    size = out.stat().st_size
    dt = time.time() - t0
    print(f'  ✓ {size:,} bytes en {dt:.1f}s')

    # Verificar integridad (parsear JSON). errors='replace' como red de
    # seguridad: si por algún motivo quedó un byte mal codificado, no
    # cancelamos todo el backup — sólo loggeamos.
    print('  Verificando integridad...')
    import json
    try:
        with open(out, encoding='utf-8') as f:
            data = json.load(f)
    except UnicodeDecodeError as e:
        print(f'  ⚠ El archivo tiene caracteres no-UTF-8 ({e}). Reintentando con latin-1...')
        with open(out, encoding='latin-1') as f:
            data = json.load(f)
    print(f'  ✓ {len(data):,} filas parseables')

    # Comprimir
    final = out
    if not args.no_compress:
        gz = out.with_suffix(out.suffix + '.gz')
        with open(out, 'rb') as fin, gzip.open(gz, 'wb', compresslevel=6) as fout:
            shutil.copyfileobj(fin, fout)
        # Borrar el .json original
        out.unlink()
        final = gz
        ratio = size / gz.stat().st_size
        print(f'  ✓ Comprimido: {gz.stat().st_size:,} bytes ({ratio:.1f}× reducción)')

    # Hash
    h = hashlib.md5(final.read_bytes()).hexdigest()
    print(f'  ✓ MD5: {h}')
    print()
    print(f'Archivo final: {final}')

    # Cleanup
    if args.keep_last is not None:
        cleanup_old_backups(args.keep_last)

    return final


def cleanup_old_backups(keep_last: int):
    """Borra los backups más viejos, dejando los `keep_last` más nuevos."""
    snaps = sorted(
        BACKUPS.glob('snapshot_*.json.gz'),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if len(snaps) <= keep_last:
        print(f'  ({len(snaps)} backups, ninguno se borra)')
        return
    to_delete = snaps[keep_last:]
    print(f'  Borrando {len(to_delete)} backups antiguos...')
    for p in to_delete:
        print(f'    rm {p.name}')
        p.unlink()


if __name__ == '__main__':
    main()
