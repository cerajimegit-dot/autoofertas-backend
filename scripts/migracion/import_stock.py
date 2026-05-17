"""
Importa STOCK desde un archivo .ods/.xlsx.

Uso:
    python scripts/migracion/import_stock.py <archivo> <branch_id>

Ejemplo:
    python scripts/migracion/import_stock.py sucursal/stock/STOCK_SUCURSAL.ods 2

Requisitos: pandas, odfpy (pip install pandas odfpy openpyxl).
"""
import sys
import os
import re
import sqlite3
import pandas as pd
from pathlib import Path

# Permitir importar helpers desde el mismo directorio
sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util
spec = importlib.util.spec_from_file_location('helpers', Path(__file__).resolve().parent / '00_helpers.py')
helpers = importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
from helpers import (norm_vin, parse_amount, parse_fecha, ENTERPRISE_ID,  # noqa
                     backup_db, fresh_copy, write_back)


def main():
    if len(sys.argv) < 3:
        print('Uso: python import_stock.py <archivo.ods> <branch_id>')
        sys.exit(1)

    archivo = sys.argv[1]
    branch_id = int(sys.argv[2])

    # Localizar la BD
    project_root = Path(__file__).resolve().parents[2]
    db_path = project_root / 'db.sqlite3'
    if not db_path.exists():
        print(f'No se encontró {db_path}')
        sys.exit(1)

    backup_db(str(db_path))
    fresh_copy(str(db_path))

    conn = sqlite3.connect('/tmp/w.db')
    cur = conn.cursor()

    # Indices
    cur.execute('SELECT id, vin FROM core_vehicle')
    veh_by_vin = {norm_vin(v): vid for vid, v in cur.fetchall() if norm_vin(v)}
    cur.execute('SELECT id, upper(name) FROM core_brand WHERE enterprise_id=?', (ENTERPRISE_ID,))
    brand_by_name = {n: bid for bid, n in cur.fetchall()}
    cur.execute('SELECT id, upper(name), brand_id FROM core_vehiclemodel WHERE enterprise_id=?', (ENTERPRISE_ID,))
    model_by_key = {(n, b): mid for mid, n, b in cur.fetchall()}

    def get_brand(name):
        key = name.strip().upper()
        if key in brand_by_name:
            return brand_by_name[key]
        cur.execute("INSERT INTO core_brand (enterprise_id, name, description, is_active, created_at, updated_at) VALUES (?, ?, '', 1, datetime('now'), datetime('now'))",
                    (ENTERPRISE_ID, name.strip()))
        bid = cur.lastrowid; brand_by_name[key] = bid; return bid

    def get_model(name, bid):
        key = (name.strip().upper(), bid)
        if key in model_by_key:
            return model_by_key[key]
        cur.execute("INSERT INTO core_vehiclemodel (enterprise_id, brand_id, name, description, is_active, created_at, updated_at) VALUES (?, ?, ?, '', 1, datetime('now'), datetime('now'))",
                    (ENTERPRISE_ID, bid, name.strip()))
        mid = cur.lastrowid; model_by_key[key] = mid; return mid

    # Leer archivo
    engine = 'odf' if archivo.lower().endswith('.ods') else None
    df = pd.read_excel(archivo, engine=engine, header=None)
    print(f'Filas en el archivo: {len(df)}')

    nuevos = 0; ya_existentes = 0; saltadas = 0
    for _, row in df.iterrows():
        first = row[0]
        if pd.isna(first):
            continue
        n_str = str(first).strip()
        if not re.match(r'^\d+(\.0+)?$', n_str.replace(',', '.')):
            continue  # no es una fila de stock real (header o separador)
        marca = row[1] if not pd.isna(row[1]) else ''
        modelo = row[2] if not pd.isna(row[2]) else ''
        color = str(row[3]).strip() if not pd.isna(row[3]) else ''
        year = row[4]
        chasis = row[5]
        if pd.isna(year) or pd.isna(chasis) or not str(marca).strip() or not str(modelo).strip():
            saltadas += 1; continue
        fob = parse_amount(row[6])
        flete = parse_amount(row[7])
        dispatch = parse_amount(row[8])
        gas = parse_amount(row[9])
        precio = parse_amount(row[10]) if len(row) > 10 else 0

        n = norm_vin(chasis)
        if n in veh_by_vin:
            ya_existentes += 1
            continue

        bid = get_brand(str(marca))
        mid = get_model(str(modelo), bid)
        cur.execute("""INSERT INTO core_vehicle
            (enterprise_id, branch_id, brand_id, model_id, year, vin, license_plate, color, mileage,
             fob, container, dispatch, cam_vol, price, currency, state, description,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, '', ?, 0,
                    ?, ?, ?, ?, ?, 'PYG', 'available', '',
                    datetime('now'), datetime('now'))""",
            (ENTERPRISE_ID, branch_id, bid, mid, int(year), str(chasis).strip(), color or '',
             float(fob), float(flete), float(dispatch), float(gas), float(precio)))
        veh_by_vin[n] = cur.lastrowid
        nuevos += 1

    conn.commit()

    print(f'\n>> Nuevos: {nuevos}')
    print(f'>> Ya existían: {ya_existentes}')
    print(f'>> Saltadas: {saltadas}')

    cur.execute('PRAGMA integrity_check'); print('Integridad:', cur.fetchone()[0])
    conn.close()
    write_back('/tmp/w.db', str(db_path))


if __name__ == '__main__':
    main()
