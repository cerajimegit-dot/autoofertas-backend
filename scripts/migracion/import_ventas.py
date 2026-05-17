"""
Importa VENTAS desde un archivo XLSX/ODS anual.

Uso:
    python scripts/migracion/import_ventas.py <archivo> <branch_id>

Ejemplo:
    python scripts/migracion/import_ventas.py sucursal/ventas/VENTAS_2025.xlsx 2

El archivo debe tener la estructura típica:
    col 0: codigo (CMnn/yy o MC nn/yyyy)
    col 1: marca, col 2: modelo, col 3: color, col 4: año, col 5: chasis
    col 6: fob, col 7: cigueña, col 8: despacho, col 9: gas
    col 11: precio venta, col 13: condicion (CONTADO/CREDITO), col 14: fecha
"""
import sys
import os
import re
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util
spec = importlib.util.spec_from_file_location('helpers', Path(__file__).resolve().parent / '00_helpers.py')
helpers = importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
from helpers import (norm_vin, parse_amount, parse_fecha, normalize_cm,  # noqa
                     ENTERPRISE_ID, PAY_CONTADO, PAY_CREDITO, MESES,
                     backup_db, fresh_copy, write_back)


def main():
    if len(sys.argv) < 3:
        print('Uso: python import_ventas.py <archivo> <branch_id>')
        sys.exit(1)

    archivo = sys.argv[1]
    branch_id = int(sys.argv[2])

    project_root = Path(__file__).resolve().parents[2]
    db_path = project_root / 'db.sqlite3'

    backup_db(str(db_path))
    fresh_copy(str(db_path))

    conn = sqlite3.connect('/tmp/w.db')
    cur = conn.cursor()

    cur.execute('SELECT id, vin FROM core_vehicle')
    veh_by_vin = {norm_vin(v): vid for vid, v in cur.fetchall() if norm_vin(v)}
    cur.execute('SELECT id, sale_number FROM core_sale WHERE sale_number IS NOT NULL')
    sale_by_code = {sn.upper(): sid for sid, sn in cur.fetchall()}
    cur.execute('SELECT id, upper(name) FROM core_brand WHERE enterprise_id=?', (ENTERPRISE_ID,))
    brand_by_name = {n: bid for bid, n in cur.fetchall()}
    cur.execute('SELECT id, upper(name), brand_id FROM core_vehiclemodel WHERE enterprise_id=?', (ENTERPRISE_ID,))
    model_by_key = {(n, b): mid for mid, n, b in cur.fetchall()}

    def get_brand(name):
        key = name.strip().upper()
        if key in brand_by_name: return brand_by_name[key]
        cur.execute("INSERT INTO core_brand (enterprise_id, name, description, is_active, created_at, updated_at) VALUES (?, ?, '', 1, datetime('now'), datetime('now'))", (ENTERPRISE_ID, name.strip()))
        bid = cur.lastrowid; brand_by_name[key] = bid; return bid

    def get_model(name, bid):
        key = (name.strip().upper(), bid)
        if key in model_by_key: return model_by_key[key]
        cur.execute("INSERT INTO core_vehiclemodel (enterprise_id, brand_id, name, description, is_active, created_at, updated_at) VALUES (?, ?, ?, '', 1, datetime('now'), datetime('now'))", (ENTERPRISE_ID, bid, name.strip()))
        mid = cur.lastrowid; model_by_key[key] = mid; return mid

    def get_vehicle(vin, bid, mid, year, color, fob, flete, despacho, gas, precio, state='sold'):
        n = norm_vin(vin)
        if n in veh_by_vin: return veh_by_vin[n], False
        cur.execute("""INSERT INTO core_vehicle
            (enterprise_id, branch_id, brand_id, model_id, year, vin, license_plate, color, mileage,
             fob, container, dispatch, cam_vol, price, currency, state, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, '', ?, 0, ?, ?, ?, ?, ?, 'PYG', ?, '', datetime('now'), datetime('now'))""",
            (ENTERPRISE_ID, branch_id, bid, mid, int(year), str(vin).strip(), color or '',
             float(fob), float(flete), float(despacho), float(gas), float(precio), state))
        veh_by_vin[n] = cur.lastrowid
        return cur.lastrowid, True

    engine = 'odf' if archivo.lower().endswith('.ods') else None
    df = pd.read_excel(archivo, engine=engine, header=None)
    print(f'Filas en el archivo: {len(df)}')

    s_created = v_created = 0; saltadas = []
    for _, row in df.iterrows():
        cm = row[0]
        if pd.isna(cm): continue
        cm_str = str(cm).strip()
        # Aceptar 'CM' o 'MC' al inicio
        if not re.match(r'^(CM|MC)\s*\d+', cm_str.upper()): continue
        cm_norm = normalize_cm(cm_str)
        if not cm_norm or cm_norm.upper() in sale_by_code:
            saltadas.append((cm_norm, 'duplicada')); continue

        marca = row[1] if not pd.isna(row[1]) else ''
        modelo = row[2] if not pd.isna(row[2]) else ''
        color = str(row[3]).strip() if not pd.isna(row[3]) else ''
        yr = row[4]; chasis = row[5]
        if pd.isna(yr) or pd.isna(chasis):
            saltadas.append((cm_norm, 'datos faltantes')); continue
        fob = parse_amount(row[6]); flete = parse_amount(row[7])
        despacho = parse_amount(row[8]); gas = parse_amount(row[9])
        precio = parse_amount(row[11]) if len(row) > 11 else 0
        cond = str(row[13]).strip().upper() if len(row) > 13 and not pd.isna(row[13]) else ''
        fecha = row[14] if len(row) > 14 else None
        sale_dt = parse_fecha(fecha)
        if not sale_dt:
            saltadas.append((cm_norm, 'sin fecha')); continue

        bid = get_brand(str(marca)); mid = get_model(str(modelo), bid)
        vid, created = get_vehicle(chasis, bid, mid, yr, color, fob, flete, despacho, gas, precio)
        if created: v_created += 1
        pf = PAY_CONTADO if 'CONTADO' in cond else (PAY_CREDITO if 'CRED' in cond else None)

        cur.execute("""INSERT INTO core_sale
            (enterprise_id, branch_id, sale_number, sale_date, customer_id, vehicle_id,
             unit_price, discount, total_price, down_payment, payment_form_id, seller_id,
             status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, NULL, ?, ?, 0, ?, 0, ?, NULL, 'completed', '', datetime('now'), datetime('now'))""",
            (ENTERPRISE_ID, branch_id, cm_norm, f'{sale_dt.isoformat()} 12:00:00', vid,
             float(precio), float(precio), pf))
        sale_by_code[cm_norm.upper()] = cur.lastrowid
        s_created += 1

    conn.commit()
    print(f'\n>> Ventas creadas: {s_created}')
    print(f'>> Vehiculos nuevos: {v_created}')
    print(f'>> Saltadas: {len(saltadas)}')
    for sk in saltadas[:10]: print('  ', sk)

    cur.execute('PRAGMA integrity_check'); print('\nIntegridad:', cur.fetchone()[0])
    conn.close()
    write_back('/tmp/w.db', str(db_path))


if __name__ == '__main__':
    main()
