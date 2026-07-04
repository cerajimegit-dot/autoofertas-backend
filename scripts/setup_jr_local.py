"""Genera el paquete completo que necesita el Jr para empezar a trabajar.

Orquesta:
  1. obfuscate_db.py -> db_jr.sqlite3 + obfuscation_mapping.csv
  2. extract_flujo_unmatched.py -> docs/jr/flujo_unmatched.csv
  3. Copia el README y la guia a docs/jr/

PRODUCTO PARA EL Jr (carpeta `docs/jr/paquete_jr/`):
  - db_jr.sqlite3       <- BD ofuscada
  - flujo_unmatched.csv <- las lineas a investigar
  - README_JR.md        <- como arrancar
  - JR_CASH_MATCHING.md <- guia completa

QUEDA CON EL SENIOR:
  - obfuscation_mapping.csv (mapeo customer/vehicle real -> ofuscado)
  - _name_mapping.csv (mapeo nombres del flujo -> Cliente_A/B/C...)

USO:
    DB_ENGINE=sqlite python scripts/setup_jr_local.py \
        --flujo "STOCK/junio2026/FLUJO DE CAJA MAYO 2.026 -.ods"
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def run(cmd, check=True):
    print(f'\n  > {" ".join(str(c) for c in cmd)}')
    env = os.environ.copy()
    env['DB_ENGINE'] = 'sqlite'
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    if check and result.returncode != 0:
        print(f'  ERROR: comando fallo con code {result.returncode}')
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--flujo', required=True,
                    help='Ruta al archivo de flujo de caja .ods')
    p.add_argument('--output-dir', default='docs/jr/paquete_jr',
                    help='Directorio destino del paquete (default docs/jr/paquete_jr)')
    args = p.parse_args()

    flujo_path = Path(args.flujo)
    if not flujo_path.exists():
        print(f'  No existe el archivo flujo: {flujo_path}')
        sys.exit(1)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    print(f'  Directorio de salida: {output.resolve()}')

    # ----- 1. Generar BD ofuscada -----
    print('\n  === Paso 1/3: Generar BD ofuscada ===')
    db_dest = output / 'db_jr.sqlite3'
    mapping_dest = ROOT / 'obfuscation_mapping.csv'  # queda fuera del paquete
    run([
        PY, 'scripts/obfuscate_db.py',
        '--output', str(db_dest),
        '--mapping', str(mapping_dest),
    ])

    # ----- 2. Generar CSV de PAGO CUOTA sin match -----
    print('\n  === Paso 2/3: Extraer lineas PAGO CUOTA sin match ===')
    csv_dest = output / 'flujo_unmatched.csv'
    name_map_dest = ROOT / 'docs/jr/_name_mapping.csv'  # queda fuera del paquete
    run([
        PY, 'scripts/extract_flujo_unmatched.py',
        str(flujo_path),
        '--out', str(csv_dest),
        '--name-mapping-out', str(name_map_dest),
    ])

    # ----- 3. Copiar guia y README -----
    print('\n  === Paso 3/3: Copiar documentacion ===')
    docs_dir = ROOT / 'docs'

    # JR_CASH_MATCHING.md
    src_guide = docs_dir / 'JR_CASH_MATCHING.md'
    if src_guide.exists():
        shutil.copy2(src_guide, output / 'JR_CASH_MATCHING.md')
        print(f'  Copiado: JR_CASH_MATCHING.md')
    else:
        print(f'  (no encontre {src_guide})')

    # DB_SCHEMA.md
    src_schema = docs_dir / 'DB_SCHEMA.md'
    if src_schema.exists():
        shutil.copy2(src_schema, output / 'DB_SCHEMA.md')
        print(f'  Copiado: DB_SCHEMA.md')

    # README_JR.md (lo generamos aqui)
    readme_content = '''# Paquete Jr — empezar a trabajar

Contenido de este paquete:

| Archivo | Para que |
|---|---|
| `db_jr.sqlite3` | BD ofuscada del sistema. Copiala a `playa/db.sqlite3` |
| `flujo_unmatched.csv` | Las lineas que tenes que investigar (~42 esperadas) |
| `JR_CASH_MATCHING.md` | Guia completa del proceso |
| `DB_SCHEMA.md` | Documentacion del modelo de datos |

## Empezar en 5 minutos

1. Cloná el repo: `git clone https://github.com/cerajimegit-dot/autoofertas-backend.git playa`
2. Setup venv:
   ```
   cd playa
   python -m venv venv
   venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
3. Copia la BD: `copy db_jr.sqlite3 db.sqlite3`
4. `.env`: dejá `DB_ENGINE=sqlite`
5. Abrí JR_CASH_MATCHING.md y seguí los pasos.
6. Abrí flujo_unmatched.csv en Excel — esa es tu lista de trabajo.

Login del sistema: cualquier usuario + password `demo1234`.

Cualquier duda, contactá al senior con el `file_row_id` del CSV.
'''
    with open(output / 'README_JR.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f'  Generado: README_JR.md')

    print(f'\n  ✓ Paquete listo en: {output.resolve()}')
    print(f'  Pasos al Jr:')
    for entry in output.iterdir():
        if entry.is_file():
            print(f'    - {entry.name}  ({entry.stat().st_size:,} bytes)')
    print(f'\n  Archivos que QUEDAN CON EL SENIOR (NO pasar al Jr):')
    print(f'    - {mapping_dest}')
    print(f'    - {name_map_dest}')


if __name__ == '__main__':
    main()
