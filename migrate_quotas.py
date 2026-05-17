#!/usr/bin/env python3
"""
Script de migración de cuotas desde archivos ODS al sistema Playa de Autos.
Trabaja directamente con SQLite sin necesidad de Django.

Uso:
    python migrate_quotas.py --dry-run          # Simular sin tocar BD
    python migrate_quotas.py --execute          # Ejecutar migración real
    python migrate_quotas.py --verify           # Verificar integridad post-migración
"""

import sqlite3
import pandas as pd
import re
import os
import sys
import json
import hashlib
import shutil
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# CONFIGURACIÓN
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('MIGRATE_DB', str(BASE_DIR / "db.sqlite3")))
ODS_FOLDER = BASE_DIR / "cuotas"
ENTERPRISE_ID = 3   # AUTO OFERTAS
BRANCH_ID = 1       # CASA CENTRAL
REPORT_DIR = BASE_DIR / "migration_reports"

# ============================================================
# DATACLASSES
# ============================================================

@dataclass
class QuotaRow:
    quota_number: int
    total_plan: int
    due_date: date
    amount: Decimal
    payment_date: Optional[date]
    payment_method: str
    status: str  # paid, pending, overdue


@dataclass
class ODSData:
    filename: str
    client_name: str
    phone: str
    vehicle_desc: str
    chassis: Optional[str]
    cm_code: Optional[str]
    sale_number_from_filename: Optional[str]
    deuda_total: Optional[Decimal]
    entrega_inicial: Optional[Decimal]
    venta_total: Optional[Decimal]
    quotas: list = field(default_factory=list)
    guarantor_name: Optional[str] = None
    guarantor_phone: Optional[str] = None
    parse_warnings: list = field(default_factory=list)


@dataclass
class MatchResult:
    sale_id: Optional[int] = None
    sale_number: Optional[str] = None
    customer_name: Optional[str] = None
    score: float = 0.0
    level: str = "no_match"  # exact, probable, ambiguous, no_match, already_imported
    method: str = ""
    existing_quotas: int = 0


# ============================================================
# PARSER DE ODS
# ============================================================

def parse_money(value) -> Optional[Decimal]:
    """Convierte montos en formato paraguayo a Decimal."""
    if pd.isna(value):
        return None
    s = str(value).strip().rstrip('.-').rstrip('-').strip()
    s = s.replace('GS', '').replace('Gs', '').replace('gs', '').strip()
    s = s.replace(' ', '')

    # Formato paraguayo: 2.000.000
    if re.match(r'^\d{1,3}(\.\d{3})+$', s):
        s = s.replace('.', '')

    # Limpiar caracteres restantes
    s = re.sub(r'[^\d]', '', s)

    try:
        return Decimal(s) if s else None
    except (InvalidOperation, ValueError):
        return None


def parse_date(value) -> Optional[date]:
    """Convierte valores de fecha del ODS."""
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in ['%Y-%m-%d', '%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
        try:
            return datetime.strptime(s.split()[0], fmt).date()
        except ValueError:
            continue
    return None


def extract_chassis(vehicle_line: str) -> Optional[str]:
    """Extrae número de chassis de la línea de vehículo."""
    patterns = [
        r'CHAS[IS]*[:\s]+([A-Z0-9-]+)',
        r'CHASIS[:\s]+([A-Z0-9-]+)',
    ]
    for p in patterns:
        m = re.search(p, vehicle_line.upper())
        if m:
            chassis = m.group(1).strip(' .-')
            # Extraer solo la parte numérica final si tiene prefijo alfanumérico
            # Ej: SCP90-0014064 -> 0014064, KSP130-0006142 -> 0006142
            parts = chassis.split('-')
            if len(parts) > 1:
                return parts[-1].lstrip('0') or parts[-1]  # Sin leading zeros
            return chassis.lstrip('0') or chassis
    return None


def extract_sale_number_from_filename(filename: str) -> Optional[str]:
    """Extrae el número de venta del nombre del archivo."""
    m = re.match(r'^(\d+)', filename)
    return m.group(1) if m else None


def parse_ods_file(filepath: str) -> ODSData:
    """Parsea un archivo ODS y retorna datos estructurados."""
    path = Path(filepath)
    df = pd.read_excel(filepath, engine='odf', header=None)

    warnings = []

    # Encabezado
    client_name = str(df.iloc[0, 0]).strip() if pd.notna(df.iloc[0, 0]) else ''
    phone_raw = str(df.iloc[1, 0]).strip() if pd.notna(df.iloc[1, 0]) else ''
    vehicle_desc = str(df.iloc[2, 0]).strip() if pd.notna(df.iloc[2, 0]) else ''

    chassis = extract_chassis(vehicle_desc)
    if not chassis:
        warnings.append(f"CHASSIS no encontrado en: {vehicle_desc}")

    # Limpiar teléfono
    phone = re.sub(r'[^0-9]', '', phone_raw)

    # Cuotas
    quotas = []
    summary_start = None

    for i in range(4, len(df)):
        val0 = str(df.iloc[i, 0]) if pd.notna(df.iloc[i, 0]) else ''

        if 'DEUDA' in val0.upper():
            summary_start = i
            break

        if not val0 or val0 == 'nan':
            continue

        due_date = parse_date(df.iloc[i, 0])
        doc_str = str(df.iloc[i, 1]) if pd.notna(df.iloc[i, 1]) else ''
        amount = parse_money(df.iloc[i, 2])
        payment_date = parse_date(df.iloc[i, 3])
        forma = str(df.iloc[i, 4]).strip() if pd.notna(df.iloc[i, 4]) else ''

        if not due_date or not amount:
            warnings.append(f"Fila {i}: no se pudo parsear fecha ({df.iloc[i, 0]}) o monto ({df.iloc[i, 2]})")
            continue

        # Parsear DOC
        quota_num, total_plan = 0, 0
        doc_match = re.match(r'(\d+)/(\d+)', doc_str)
        if doc_match:
            quota_num = int(doc_match.group(1))
            total_plan = int(doc_match.group(2))

        # Estado
        if forma == 'VENCIDO':
            status = 'overdue'
        elif payment_date:
            status = 'paid'
        else:
            status = 'pending'

        quotas.append(QuotaRow(
            quota_number=quota_num,
            total_plan=total_plan,
            due_date=due_date,
            amount=amount,
            payment_date=payment_date,
            payment_method=forma if forma != 'VENCIDO' else '',
            status=status,
        ))

    # Normalizar total_plan (usar el valor más frecuente para corregir typos como 4/34)
    if quotas:
        plan_values = [q.total_plan for q in quotas if q.total_plan > 0]
        if plan_values:
            from collections import Counter
            most_common_plan = Counter(plan_values).most_common(1)[0][0]
            for q in quotas:
                if q.total_plan != most_common_plan:
                    warnings.append(f"Cuota {q.quota_number}: total_plan corregido de {q.total_plan} a {most_common_plan}")
                    q.total_plan = most_common_plan

    # Sección resumen
    cm_code = None
    deuda_total = None
    entrega_inicial = None
    venta_total = None
    guarantor_name = None
    guarantor_phone = None

    if summary_start:
        deuda_total = parse_money(df.iloc[summary_start, 2])

        for i in range(summary_start + 1, len(df)):
            val = str(df.iloc[i, 0]) if pd.notna(df.iloc[i, 0]) else ''
            val_upper = val.upper()

            cm_match = re.match(r'(CM\d+/\d+)', val)
            if cm_match:
                cm_code = cm_match.group(1)

            if 'ENTREGA' in val_upper:
                entrega_inicial = parse_money(val)

            if 'VENTA TOTAL' in val_upper:
                venta_total = parse_money(val)

            # Garante
            if i > summary_start + 4 and val and val != 'nan':
                if 'CUOTA' not in val_upper and 'SALDO' not in val_upper and 'ENTREGA' not in val_upper and 'VENTA' not in val_upper:
                    if not guarantor_name and re.match(r'^[A-ZÑÁÉÍÓÚ\s\.]+$', val.strip()):
                        guarantor_name = val.strip()
                    elif 'GARANTE' in val_upper or re.search(r'\d{4}[-.]?\d{3}', val):
                        if not guarantor_phone:
                            guarantor_phone = val.strip()

    sale_num = extract_sale_number_from_filename(path.stem)

    return ODSData(
        filename=path.name,
        client_name=client_name,
        phone=phone,
        vehicle_desc=vehicle_desc,
        chassis=chassis,
        cm_code=cm_code,
        sale_number_from_filename=sale_num,
        deuda_total=deuda_total,
        entrega_inicial=entrega_inicial,
        venta_total=venta_total,
        quotas=quotas,
        guarantor_name=guarantor_name,
        guarantor_phone=guarantor_phone,
        parse_warnings=warnings,
    )


# ============================================================
# MOTOR DE MATCHING
# ============================================================

def normalize_name(name: str) -> str:
    """Normaliza nombre para comparación."""
    name = name.upper().strip()
    # Quitar DE, DEL, etc.
    name = re.sub(r'\b(DE|DEL|LA|LOS|LAS)\b', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def vin_matches(ods_chassis: str, db_vin: str) -> bool:
    """Verifica si un chassis del ODS coincide con un VIN de la BD.
    El chassis puede ser parcial. Los VINs en BD pueden tener prefijos/sufijos."""
    if not ods_chassis or not db_vin:
        return False
    ods_clean = ods_chassis.lstrip('0')
    db_clean = db_vin.lstrip('0')
    # Match si uno contiene al otro
    return ods_clean in db_clean or db_clean in ods_clean


def find_matches(ods_data: ODSData, conn: sqlite3.Connection) -> list:
    """Busca ventas candidatas en la BD."""
    c = conn.cursor()
    results = []

    # NIVEL 1: Match por VIN/chassis
    if ods_data.chassis:
        c.execute('''
            SELECT s.id, s.sale_number, s.total_price, s.customer_id,
                   COALESCE(cu.first_name, '') || ' ' || COALESCE(cu.last_name, '') as customer_name,
                   v.vin, v.year,
                   (SELECT COUNT(*) FROM core_quotum q WHERE q.sale_id = s.id) as quota_count
            FROM core_sale s
            LEFT JOIN core_customer cu ON cu.id = s.customer_id
            LEFT JOIN core_vehicle v ON v.id = s.vehicle_id
            WHERE s.enterprise_id = ?
        ''', (ENTERPRISE_ID,))

        for row in c.fetchall():
            sale_id, sale_num, total, cust_id, cust_name, db_vin, db_year, q_count = row
            if db_vin and vin_matches(ods_data.chassis, db_vin):
                level = "already_imported" if q_count > 0 else "exact"
                results.append(MatchResult(
                    sale_id=sale_id,
                    sale_number=sale_num,
                    customer_name=cust_name.strip(),
                    score=95.0,
                    level=level,
                    method=f"VIN match: ODS={ods_data.chassis} DB={db_vin}",
                    existing_quotas=q_count,
                ))

    if results:
        # Si encontramos match exacto por VIN, retornar
        exact = [r for r in results if r.level == "exact"]
        if exact:
            return exact[:5]
        return results[:5]

    # NIVEL 2: Match heurístico por nombre de cliente
    ods_name = normalize_name(ods_data.client_name)
    file_num = ods_data.sale_number_from_filename

    c.execute('''
        SELECT s.id, s.sale_number, s.total_price,
               COALESCE(cu.first_name, '') || ' ' || COALESCE(cu.last_name, '') as customer_name,
               v.vin, v.year,
               (SELECT COUNT(*) FROM core_quotum q WHERE q.sale_id = s.id) as quota_count
        FROM core_sale s
        LEFT JOIN core_customer cu ON cu.id = s.customer_id
        LEFT JOIN core_vehicle v ON v.id = s.vehicle_id
        WHERE s.enterprise_id = ?
    ''', (ENTERPRISE_ID,))

    for row in c.fetchall():
        sale_id, sale_num, total, cust_name, db_vin, db_year, q_count = row
        db_name = normalize_name(cust_name.strip())

        score = 0.0

        # Score por nombre (50%)
        name_ratio = SequenceMatcher(None, ods_name, db_name).ratio()
        score += name_ratio * 50

        # Score por año del vehículo (20%)
        if db_year and str(db_year) in ods_data.vehicle_desc:
            score += 20

        # Score por monto total (20%)
        if ods_data.venta_total and total:
            try:
                diff = abs(float(ods_data.venta_total) - float(total))
                if diff < float(total) * 0.05:
                    score += 20
                elif diff < float(total) * 0.15:
                    score += 10
            except (ValueError, TypeError):
                pass

        # Score bonus por número de archivo en sale_number (10%)
        if file_num and file_num in str(sale_num):
            score += 10

        if score >= 55:
            level = "already_imported" if q_count > 0 else (
                "probable" if score >= 80 else "ambiguous"
            )
            results.append(MatchResult(
                sale_id=sale_id,
                sale_number=sale_num,
                customer_name=cust_name.strip(),
                score=score,
                level=level,
                method="heuristic",
                existing_quotas=q_count,
            ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:5]


# ============================================================
# IMPORTADOR
# ============================================================

STATUS_MAP = {
    'paid': 'paid',
    'pending': 'pending',
    'overdue': 'overdue',
}


def import_quotas(ods_data: ODSData, sale_id: int, conn: sqlite3.Connection, dry_run: bool = True) -> dict:
    """Importa cuotas de un ODS a una venta existente."""
    result = {
        'success': False,
        'quotas_created': 0,
        'warnings': [],
        'errors': [],
    }

    c = conn.cursor()

    # Verificar que la venta no tenga cuotas ya
    c.execute('SELECT COUNT(*) FROM core_quotum WHERE sale_id = ?', (sale_id,))
    existing = c.fetchone()[0]
    if existing > 0:
        result['errors'].append(f"Venta {sale_id} ya tiene {existing} cuotas. Saltando.")
        return result

    # Obtener customer_id de la venta
    c.execute('SELECT customer_id FROM core_sale WHERE id = ?', (sale_id,))
    row = c.fetchone()
    if not row:
        result['errors'].append(f"Venta {sale_id} no encontrada.")
        return result
    customer_id = row[0]

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for q in ods_data.quotas:
        if dry_run:
            result['quotas_created'] += 1
            continue

        try:
            c.execute('''
                INSERT INTO core_quotum
                (enterprise_id, sale_id, customer_id, quota_number, plan_name, total_plan,
                 amount, interest, due_date, payment_date, status, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ENTERPRISE_ID,
                sale_id,
                customer_id,
                q.quota_number,
                f"{q.total_plan} cuotas",  # plan_name
                q.total_plan,
                str(q.amount),
                '0',  # interest
                q.due_date.isoformat(),
                q.payment_date.isoformat() if q.payment_date else None,
                STATUS_MAP.get(q.status, 'pending'),
                f"Migrado de {ods_data.filename}. Forma: {q.payment_method}",
                now,
                now,
            ))
            result['quotas_created'] += 1
        except Exception as e:
            result['errors'].append(f"Error cuota {q.quota_number}: {e}")

    if not dry_run and not result['errors']:
        conn.commit()

    result['success'] = len(result['errors']) == 0
    if dry_run:
        result['success'] = True

    return result


def create_sale_and_import(ods_data: ODSData, conn: sqlite3.Connection, dry_run: bool = True) -> dict:
    """Crea una venta nueva y luego importa las cuotas."""
    result = {
        'sale_id': None,
        'sale_number': None,
        'customer_id': None,
        'customer_created': False,
        'quotas_created': 0,
        'warnings': [],
        'errors': [],
    }

    c = conn.cursor()

    # 1. Buscar o crear cliente
    # Buscar por nombre similar en clientes existentes
    c.execute('''
        SELECT id, first_name, last_name, document_number
        FROM core_customer WHERE enterprise_id = ?
    ''', (ENTERPRISE_ID,))

    ods_name_norm = normalize_name(ods_data.client_name)
    best_customer = None
    best_ratio = 0

    for cid, fname, lname, doc in c.fetchall():
        db_name_norm = normalize_name(f"{fname} {lname}")
        ratio = SequenceMatcher(None, ods_name_norm, db_name_norm).ratio()
        if ratio > best_ratio and ratio >= 0.80:
            best_ratio = ratio
            best_customer = (cid, fname, lname, doc)

    customer_id = None
    if best_customer:
        customer_id = best_customer[0]
        result['warnings'].append(
            f"Cliente existente reutilizado: {best_customer[1]} {best_customer[2]} "
            f"(doc={best_customer[3]}, ratio={best_ratio:.2f})"
        )
    else:
        # Crear nuevo
        parts = ods_data.client_name.strip().split()
        if len(parts) >= 4:
            first_name = ' '.join(parts[:2])
            last_name = ' '.join(parts[2:])
        elif len(parts) == 3:
            first_name = parts[0]
            last_name = ' '.join(parts[1:])
        elif len(parts) == 2:
            first_name = parts[0]
            last_name = parts[1]
        else:
            first_name = ods_data.client_name
            last_name = ''

        file_num = ods_data.sale_number_from_filename or 'UNK'
        doc_number = f"MIGQ-{file_num}"

        if not dry_run:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute('''
                INSERT INTO core_customer
                (enterprise_id, is_generic, first_name, last_name, document_type,
                 document_number, email, phone, address, city, notes, created_at, updated_at)
                VALUES (?, 0, ?, ?, 'ci', ?, '', ?, '', '', ?, ?, ?)
            ''', (
                ENTERPRISE_ID, first_name, last_name, doc_number,
                ods_data.phone or '',
                f"Creado por migración desde {ods_data.filename}",
                now, now,
            ))
            customer_id = c.lastrowid
        else:
            customer_id = -1  # placeholder

        result['customer_created'] = True
        result['warnings'].append(f"Cliente nuevo: {first_name} {last_name} (doc={doc_number})")

    result['customer_id'] = customer_id

    # 2. Crear venta
    sale_number = ods_data.cm_code or f"MIGQ-{ods_data.sale_number_from_filename or 'UNK'}"

    # Verificar que no exista
    c.execute('SELECT id FROM core_sale WHERE sale_number = ?', (sale_number,))
    if c.fetchone():
        sale_number = f"{sale_number}-DUP{datetime.now():%H%M%S}"
        result['warnings'].append(f"sale_number duplicado, usando: {sale_number}")

    total = ods_data.venta_total or sum(q.amount for q in ods_data.quotas)
    entrega = ods_data.entrega_inicial or Decimal('0')

    notes = f"Venta creada por migración de cuotas desde {ods_data.filename}."
    if ods_data.entrega_inicial:
        notes += f"\nEntrega inicial: {ods_data.entrega_inicial}"
    if ods_data.deuda_total:
        notes += f"\nDeuda total: {ods_data.deuda_total}"
    if ods_data.guarantor_name:
        notes += f"\nGarante: {ods_data.guarantor_name}"
        if ods_data.guarantor_phone:
            notes += f" - {ods_data.guarantor_phone}"

    if not dry_run:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''
            INSERT INTO core_sale
            (enterprise_id, branch_id, sale_number, sale_date, customer_id, vehicle_id,
             unit_price, discount, total_price, payment_form_id, seller_id,
             status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, NULL, ?, 0, ?, 3, NULL, 'pending', ?, ?, ?)
        ''', (
            ENTERPRISE_ID, BRANCH_ID, sale_number, now,
            customer_id,
            str(total), str(total),
            notes, now, now,
        ))
        sale_id = c.lastrowid
        conn.commit()
    else:
        sale_id = -1

    result['sale_id'] = sale_id
    result['sale_number'] = sale_number

    # 3. Importar cuotas
    if not dry_run:
        import_result = import_quotas(ods_data, sale_id, conn, dry_run=False)
        result['quotas_created'] = import_result['quotas_created']
        result['errors'].extend(import_result['errors'])
    else:
        result['quotas_created'] = len(ods_data.quotas)

    return result


# ============================================================
# ORQUESTADOR PRINCIPAL
# ============================================================

def run_migration(dry_run=True):
    """Ejecuta la migración completa."""
    REPORT_DIR.mkdir(exist_ok=True)

    print(f"\n{'='*70}")
    print(f"  MIGRACIÓN DE CUOTAS - {'DRY RUN (simulación)' if dry_run else 'EJECUCIÓN REAL'}")
    print(f"{'='*70}")
    print(f"  BD: {DB_PATH}")
    print(f"  ODS: {ODS_FOLDER}")
    print(f"  Enterprise: {ENTERPRISE_ID} | Branch: {BRANCH_ID}")
    print(f"{'='*70}\n")

    if not dry_run:
        # Backup
        backup_path = BASE_DIR / f"db_backup_{datetime.now():%Y%m%d_%H%M%S}.sqlite3"
        shutil.copy2(DB_PATH, backup_path)
        print(f"  BACKUP creado: {backup_path}\n")

    conn = sqlite3.connect(str(DB_PATH))
    files = sorted(ODS_FOLDER.glob('*.ods'))

    print(f"  Archivos a procesar: {len(files)}\n")

    report = {
        'timestamp': datetime.now().isoformat(),
        'mode': 'dry_run' if dry_run else 'execute',
        'total_files': len(files),
        'matched_by_vin': 0,
        'matched_by_heuristic': 0,
        'already_imported': 0,
        'new_sales_needed': 0,
        'total_quotas': 0,
        'errors': [],
        'details': [],
    }

    for idx, filepath in enumerate(files, 1):
        print(f"\n{'─'*70}")
        print(f"  [{idx}/{len(files)}] {filepath.name}")

        # 1. Parsear
        try:
            ods = parse_ods_file(str(filepath))
        except Exception as e:
            print(f"  ✗ ERROR parseando: {e}")
            report['errors'].append({'file': filepath.name, 'error': str(e)})
            continue

        for w in ods.parse_warnings:
            print(f"    ⚠ {w}")

        print(f"    Cliente: {ods.client_name}")
        print(f"    Vehículo: {ods.vehicle_desc}")
        print(f"    Chassis: {ods.chassis or 'N/A'}")
        print(f"    CM: {ods.cm_code or 'N/A'}")
        print(f"    Cuotas: {len(ods.quotas)}")
        if ods.venta_total:
            print(f"    Venta Total: {ods.venta_total:,.0f}")
        if ods.entrega_inicial:
            print(f"    Entrega: {ods.entrega_inicial:,.0f}")

        # 2. Buscar matches
        matches = find_matches(ods, conn)

        detail = {
            'file': filepath.name,
            'client': ods.client_name,
            'chassis': ods.chassis,
            'cm_code': ods.cm_code,
            'num_quotas': len(ods.quotas),
            'venta_total': str(ods.venta_total) if ods.venta_total else None,
            'action': None,
            'sale_number': None,
            'match_score': 0,
            'match_method': None,
            'quotas_imported': 0,
            'warnings': [],
        }

        if matches and matches[0].level == "already_imported":
            best = matches[0]
            print(f"    ⏭ YA IMPORTADA: Venta {best.sale_number} tiene {best.existing_quotas} cuotas")
            detail['action'] = 'skipped_already_imported'
            detail['sale_number'] = best.sale_number
            report['already_imported'] += 1

        elif matches and matches[0].level == "exact":
            best = matches[0]
            print(f"    ✓ MATCH EXACTO (VIN): Venta {best.sale_number} - {best.customer_name}")
            print(f"      Score: {best.score:.1f}% | {best.method}")

            result = import_quotas(ods, best.sale_id, conn, dry_run)
            if result['success']:
                print(f"    ✓ {result['quotas_created']} cuotas {'importadas' if not dry_run else 'a importar'}")
                report['matched_by_vin'] += 1
                report['total_quotas'] += result['quotas_created']
                detail['action'] = 'imported_vin_match'
                detail['sale_number'] = best.sale_number
                detail['match_score'] = best.score
                detail['match_method'] = best.method
                detail['quotas_imported'] = result['quotas_created']
            else:
                for e in result['errors']:
                    print(f"    ✗ {e}")
                detail['action'] = 'error'
                detail['warnings'] = result['errors']

        elif matches and matches[0].level in ("probable", "ambiguous"):
            best = matches[0]
            print(f"    ? MATCH HEURÍSTICO: Venta {best.sale_number} - {best.customer_name}")
            print(f"      Score: {best.score:.1f}% | Nivel: {best.level}")

            if best.existing_quotas > 0:
                print(f"      ⚠ Venta ya tiene {best.existing_quotas} cuotas - SALTANDO")
                detail['action'] = 'skipped_has_quotas'
                detail['sale_number'] = best.sale_number
                report['already_imported'] += 1
            elif best.score >= 75:
                # Match suficientemente bueno
                result = import_quotas(ods, best.sale_id, conn, dry_run)
                if result['success']:
                    print(f"    ✓ {result['quotas_created']} cuotas {'importadas' if not dry_run else 'a importar'}")
                    report['matched_by_heuristic'] += 1
                    report['total_quotas'] += result['quotas_created']
                    detail['action'] = 'imported_heuristic_match'
                    detail['sale_number'] = best.sale_number
                    detail['match_score'] = best.score
                    detail['match_method'] = 'heuristic'
                    detail['quotas_imported'] = result['quotas_created']
                else:
                    for e in result['errors']:
                        print(f"    ✗ {e}")
                    detail['action'] = 'error'
            else:
                print(f"      Score bajo ({best.score:.1f}%) - CREAR VENTA NUEVA")
                result = create_sale_and_import(ods, conn, dry_run)
                for w in result['warnings']:
                    print(f"      ⚠ {w}")
                print(f"    ✓ Venta {result['sale_number']}: {result['quotas_created']} cuotas")
                report['new_sales_needed'] += 1
                report['total_quotas'] += result['quotas_created']
                detail['action'] = 'new_sale_created'
                detail['sale_number'] = result['sale_number']
                detail['quotas_imported'] = result['quotas_created']
                detail['warnings'] = result['warnings']
        else:
            # Sin match
            print(f"    ✗ SIN MATCH - CREAR VENTA NUEVA")
            result = create_sale_and_import(ods, conn, dry_run)
            for w in result['warnings']:
                print(f"      ⚠ {w}")
            if result['errors']:
                for e in result['errors']:
                    print(f"    ✗ {e}")
                detail['action'] = 'error'
            else:
                print(f"    ✓ Venta {result['sale_number']}: {result['quotas_created']} cuotas")
                report['new_sales_needed'] += 1
                report['total_quotas'] += result['quotas_created']
                detail['action'] = 'new_sale_created'
                detail['sale_number'] = result['sale_number']
                detail['quotas_imported'] = result['quotas_created']
                detail['warnings'] = result['warnings']

        report['details'].append(detail)

    conn.close()

    # Reporte final
    print(f"\n\n{'='*70}")
    print(f"  REPORTE FINAL - {'DRY RUN' if dry_run else 'EJECUCIÓN'}")
    print(f"{'='*70}")
    print(f"  Archivos procesados:    {len(report['details'])}/{report['total_files']}")
    print(f"  Match por VIN:          {report['matched_by_vin']}")
    print(f"  Match heurístico:       {report['matched_by_heuristic']}")
    print(f"  Ya importadas:          {report['already_imported']}")
    print(f"  Ventas nuevas:          {report['new_sales_needed']}")
    print(f"  Total cuotas:           {report['total_quotas']}")
    print(f"  Errores:                {len(report['errors'])}")
    print(f"{'='*70}\n")

    # Guardar reporte JSON
    mode_str = 'dryrun' if dry_run else 'exec'
    report_path = REPORT_DIR / f"report_{mode_str}_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Reporte guardado: {report_path}\n")

    return report


def verify_integrity():
    """Verificación post-migración."""
    print(f"\n{'='*70}")
    print(f"  VERIFICACIÓN DE INTEGRIDAD")
    print(f"{'='*70}\n")

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    issues = []

    # 1. Cuotas duplicadas
    c.execute('''
        SELECT sale_id, quota_number, COUNT(*) as cnt
        FROM core_quotum WHERE enterprise_id = ?
        GROUP BY sale_id, quota_number HAVING cnt > 1
    ''', (ENTERPRISE_ID,))
    dupes = c.fetchall()
    if dupes:
        issues.append(f"✗ {len(dupes)} cuotas duplicadas (sale_id, quota_number)")
        for d in dupes[:5]:
            print(f"    sale_id={d[0]}, cuota #{d[1]}, count={d[2]}")
    else:
        print("  ✓ Sin cuotas duplicadas")

    # 2. Ventas sin cuotas
    c.execute('''
        SELECT s.id, s.sale_number,
               COALESCE(cu.first_name, '') || ' ' || COALESCE(cu.last_name, '') as name
        FROM core_sale s
        LEFT JOIN core_customer cu ON cu.id = s.customer_id
        WHERE s.enterprise_id = ?
        AND NOT EXISTS (SELECT 1 FROM core_quotum q WHERE q.sale_id = s.id)
        AND s.sale_number NOT LIKE 'V%'
        AND s.sale_number != 'VDUMMY'
    ''', (ENTERPRISE_ID,))
    no_quotas = c.fetchall()
    if no_quotas:
        issues.append(f"⚠ {len(no_quotas)} ventas MIG sin cuotas")
        for nq in no_quotas[:10]:
            print(f"    {nq[1]} - {nq[2]}")
    else:
        print("  ✓ Todas las ventas MIG tienen cuotas")

    # 3. Clientes placeholder
    c.execute('''
        SELECT COUNT(*) FROM core_customer
        WHERE enterprise_id = ? AND document_number LIKE 'MIGQ-%'
    ''', (ENTERPRISE_ID,))
    placeholders = c.fetchone()[0]
    if placeholders:
        issues.append(f"⚠ {placeholders} clientes con documento placeholder MIGQ-")
    print(f"  {'⚠' if placeholders else '✓'} Clientes placeholder: {placeholders}")

    # 4. Totales
    c.execute('SELECT COUNT(*) FROM core_sale WHERE enterprise_id = ?', (ENTERPRISE_ID,))
    total_sales = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM core_quotum WHERE enterprise_id = ?', (ENTERPRISE_ID,))
    total_quotas = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM core_customer WHERE enterprise_id = ?', (ENTERPRISE_ID,))
    total_customers = c.fetchone()[0]

    print(f"\n  Totales:")
    print(f"    Ventas: {total_sales}")
    print(f"    Cuotas: {total_quotas}")
    print(f"    Clientes: {total_customers}")

    # 5. Resumen por estado de cuotas
    c.execute('''
        SELECT status, COUNT(*) FROM core_quotum
        WHERE enterprise_id = ?
        GROUP BY status
    ''', (ENTERPRISE_ID,))
    print(f"\n  Cuotas por estado:")
    for status, cnt in c.fetchall():
        print(f"    {status}: {cnt}")

    conn.close()

    if not issues:
        print(f"\n  ✓ INTEGRIDAD OK - Sin problemas detectados")
    else:
        print(f"\n  ⚠ {len(issues)} problemas detectados")

    return issues


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python migrate_quotas.py --dry-run    Simular migración")
        print("  python migrate_quotas.py --execute    Ejecutar migración real")
        print("  python migrate_quotas.py --verify     Verificar integridad")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == '--dry-run':
        run_migration(dry_run=True)
    elif mode == '--execute':
        if '--yes' in sys.argv:
            run_migration(dry_run=False)
        else:
            print("\n  ⚠ MODO EJECUCIÓN REAL - los datos se modificarán")
            confirm = input("  ¿Continuar? (si/no): ").strip().lower()
            if confirm in ('si', 'sí', 's', 'yes', 'y'):
                run_migration(dry_run=False)
            else:
                print("  Cancelado.")
    elif mode == '--verify':
        verify_integrity()
    else:
        print(f"Modo desconocido: {mode}")
        sys.exit(1)
