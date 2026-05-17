"""
Importa CUOTAS desde archivos individuales por cliente (.ods) en una carpeta.

Uso:
    python scripts/migracion/import_cuotas.py <carpeta>

Ejemplo:
    python scripts/migracion/import_cuotas.py sucursal/cuotas/

Estructura esperada de cada archivo:
    R0: nombre del cliente
    R1: teléfono
    R2: descripción del vehículo + 'CHAS:' o 'CHASIS:' con el chasis
    R3: header [VTO, DOC, MONTO, FECHA, FORMA]
    R4..N: cuotas (FECHA vacía = pendiente; "VENCIDO" = vencida; fecha real = pagada)
    Después: 'DEUDA TOTAL', código CM/MC, 'ENTREGA <monto>'

Asocia cuotas a ventas existentes matcheando por código CM/MC o por chasis (VIN).
"""
import sys
import os
import re
import sqlite3
import pandas as pd
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util
spec = importlib.util.spec_from_file_location('helpers', Path(__file__).resolve().parent / '00_helpers.py')
helpers = importlib.util.module_from_spec(spec); spec.loader.exec_module(helpers)
from helpers import (norm_vin, parse_amount, parse_fecha, normalize_cm,  # noqa
                     extraer_chasis_de_texto, DOC_RE,
                     ENTERPRISE_ID, PAY_CREDITO,
                     backup_db, fresh_copy, write_back)


def dividir_nombre(full):
    parts = str(full).strip().split()
    if len(parts) == 1: return parts[0], ''
    if len(parts) == 2: return parts[0], parts[1]
    n = len(parts) // 2
    return ' '.join(parts[:n]), ' '.join(parts[n:])


def main():
    if len(sys.argv) < 2:
        print('Uso: python import_cuotas.py <carpeta>')
        sys.exit(1)

    carpeta = sys.argv[1]
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
    cur.execute("SELECT id, upper(first_name||' '||last_name) FROM core_customer")
    cust_by_name = {n.strip(): cid for cid, n in cur.fetchall()}

    today_d = date.today()
    files = sorted([os.path.join(carpeta, f) for f in os.listdir(carpeta) if f.endswith('.ods')])
    print(f'Archivos a procesar: {len(files)}')

    ok = 0; nomatch = 0; ya_tenian = 0
    for path in files:
        try: df = pd.read_excel(path, engine='odf', header=None)
        except Exception as e: print(f'  ERR leyendo {path}: {e}'); continue

        def gr(i):
            try: return [v if not pd.isna(v) else '' for v in df.iloc[i]]
            except: return []

        client_name = str(gr(0)[0] if len(gr(0)) > 0 else '').strip()
        phone = str(gr(1)[0] if len(gr(1)) > 0 else '').strip()
        chasis = extraer_chasis_de_texto(gr(2)[0] if len(gr(2)) > 0 else '')
        cm_code = entrega = None
        for i in range(len(df)):
            for v in gr(i):
                sv = str(v).upper()
                m = re.search(r'\b(MC|CM)\s*[0-9]+\s*/\s*[0-9]+\b', sv)
                if m and not cm_code: cm_code = normalize_cm(m.group(0))
                if 'ENTREGA' in sv:
                    m2 = re.search(r'ENTREGA[A-Z\s.]*([0-9.]+)', sv)
                    if m2:
                        v2 = parse_amount(m2.group(1))
                        if v2 and (entrega is None or v2 > entrega): entrega = v2

        # Match
        sale_id = None
        if cm_code and cm_code.upper() in sale_by_code:
            sale_id = sale_by_code[cm_code.upper()]
        elif chasis:
            vn = norm_vin(chasis)
            if vn and vn in veh_by_vin:
                cur.execute('SELECT id FROM core_sale WHERE vehicle_id=?', (veh_by_vin[vn],))
                r = cur.fetchone()
                if r: sale_id = r[0]
        if not sale_id:
            nomatch += 1
            print(f'  NO MATCH: {os.path.basename(path)[:40]} cm={cm_code} chasis={chasis}')
            continue

        # Cliente
        customer_id = None
        if client_name:
            nk = client_name.upper().strip()
            if nk in cust_by_name: customer_id = cust_by_name[nk]
            else:
                first, last = dividir_nombre(client_name)
                doc = f'MIG-{cm_code or os.path.basename(path)[:20]}'
                try:
                    cur.execute("""INSERT INTO core_customer
                        (enterprise_id, is_generic, first_name, last_name, document_type, document_number,
                         email, phone, address, city, notes, created_at, updated_at)
                        VALUES (?, 0, ?, ?, 'ci', ?, '', ?, '', '', ?, datetime('now'), datetime('now'))""",
                        (ENTERPRISE_ID, first, last, doc, phone, f'Importado de {os.path.basename(path)}'))
                    customer_id = cur.lastrowid; cust_by_name[nk] = customer_id
                except sqlite3.IntegrityError:
                    cur.execute('SELECT id FROM core_customer WHERE document_number=?', (doc,))
                    rr = cur.fetchone()
                    if rr: customer_id = rr[0]

        # Update sale meta
        cur.execute('SELECT customer_id, down_payment, payment_form_id FROM core_sale WHERE id=?', (sale_id,))
        cc, cdp, cpf = cur.fetchone()
        upd, vals = [], []
        if customer_id and not cc: upd.append('customer_id=?'); vals.append(customer_id)
        if entrega and float(cdp or 0) == 0: upd.append('down_payment=?'); vals.append(entrega)
        if not cpf: upd.append('payment_form_id=?'); vals.append(PAY_CREDITO)
        if upd: vals.append(sale_id); cur.execute(f"UPDATE core_sale SET {', '.join(upd)} WHERE id=?", vals)

        # Cuotas existentes (no duplicar)
        cur.execute('SELECT quota_number FROM core_quotum WHERE sale_id=?', (sale_id,))
        existing_q = {row[0] for row in cur.fetchall()}

        # Parsear cuotas
        nuevas = []; total_plan = None
        for i in range(4, len(df)):
            r = gr(i)
            if len(r) < 3: continue
            vto, doc, monto = r[0], r[1], r[2]
            fpago = r[3] if len(r) > 3 else ''
            forma = r[4] if len(r) > 4 else ''
            m = DOC_RE.match(str(doc).strip())  # tolera "1/8" Y "1/8."
            if not m: continue
            nq, total = int(m.group(1)), int(m.group(2))
            total_plan = total
            if nq in existing_q: continue
            amt = parse_amount(monto)
            vto_dt = parse_fecha(vto)
            pago_dt = parse_fecha(fpago)
            if not vto_dt or not amt: continue
            is_venc = str(fpago).strip().upper() == 'VENCIDO'
            if pago_dt: status = 'paid'
            elif is_venc or vto_dt < today_d: status = 'overdue'
            else: status = 'pending'
            nuevas.append({'n': nq, 'total': total, 'amt': amt, 'due': vto_dt, 'pay': pago_dt,
                           'status': status, 'forma': str(forma).strip()})

        if not nuevas:
            ya_tenian += 1; continue

        plan_name = f'{total_plan} cuotas' if total_plan else 'Plan'
        for q in nuevas:
            cur.execute("""INSERT OR IGNORE INTO core_quotum
                (enterprise_id, sale_id, customer_id, quota_number, plan_name, total_plan,
                 amount, interest, due_date, payment_date, cancelled_date, status, notes,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, NULL, ?, ?, datetime('now'), datetime('now'))""",
                (ENTERPRISE_ID, sale_id, customer_id, q['n'], plan_name, q['total'], q['amt'],
                 q['due'].isoformat(), q['pay'].isoformat() if q['pay'] else None,
                 q['status'], f'Forma: {q["forma"]}' if q['forma'] else ''))
        ok += 1

    conn.commit()
    print(f'\n>> OK: {ok}')
    print(f'>> Sin match: {nomatch}')
    print(f'>> Sin cuotas nuevas: {ya_tenian}')

    cur.execute('PRAGMA integrity_check'); print('\nIntegridad:', cur.fetchone()[0])
    conn.close()
    write_back('/tmp/w.db', str(db_path))


if __name__ == '__main__':
    main()
