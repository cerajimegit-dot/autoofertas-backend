"""
Helpers compartidos para los scripts de migración.

Importar al principio de cada script:
    from helpers import (norm_vin, parse_amount, parse_fecha, normalize_cm, DOC_RE,
                         backup_db, fresh_copy, write_back, get_or_create)
"""
import os
import re
import sqlite3
import shutil
from datetime import date, datetime
from pathlib import Path

# ============================================================
#                  PARSERS DE DATOS DE EXCEL
# ============================================================

# Regex que tolera punto al final del número de cuota (`1/8.` o `1/8`).
# Bug histórico: sin el punto opcional perdíamos cuotas en archivos
# como `19 - EMIGDIO FARIÑA RODRIGUEZ.ods` y `23 - JUAN GILBERTO MORENO.ods`.
DOC_RE = re.compile(r'\s*([0-9]+)\s*/\s*([0-9]+)\s*[.]?\s*$')


def norm_vin(raw):
    """Normaliza un VIN/chasis para matchear entre fuentes (sin espacios,
    sin caracteres especiales, sin leading zeros, sin sufijo .0)."""
    try:
        import pandas as pd  # noqa
    except ImportError:
        pd = None
    if raw is None:
        return None
    if pd is not None and isinstance(raw, float) and pd.isna(raw):
        return None
    s = str(raw).strip().upper()
    if not s or s in ('NAN', 'NONE'):
        return None
    if re.match(r'^[0-9]+[.]0+$', s):
        s = s.split('.')[0]
    s = re.sub(r'[^A-Z0-9]', '', s)
    s = s.lstrip('0') or s  # evitar quedar con string vacío si era todo ceros
    return s or None


def parse_amount(s):
    """Parsea un monto que puede tener formato '$1.420', '252$+440$',
    '15.000.000Gs.-', '1500000', etc. Devuelve int."""
    try:
        import pandas as pd
    except ImportError:
        pd = None
    if s is None:
        return 0
    if pd is not None and isinstance(s, float) and pd.isna(s):
        return 0
    if isinstance(s, (int, float)):
        return int(s)
    s = str(s).strip()
    total = 0
    for part in s.split('+'):
        digits = re.sub(r'[^0-9]', '', part)
        if digits:
            total += int(digits)
    return total


def parse_fecha(s):
    """Parsea fecha. CRÍTICO: si recibe un Timestamp/datetime, usar año/mes/día
    explícitos — NUNCA pasar por pd.to_datetime con dayfirst, que invierte
    día y mes en strings ISO ('2026-02-10' → '2026-10-02')."""
    try:
        import pandas as pd
    except ImportError:
        pd = None
    if s is None:
        return None
    if pd is not None and isinstance(s, float) and pd.isna(s):
        return None
    # Timestamp/datetime/date — tomar componentes directos
    if hasattr(s, 'year') and hasattr(s, 'month') and hasattr(s, 'day'):
        try:
            return date(s.year, s.month, s.day)
        except Exception:
            pass
    s = str(s).strip()
    if not s or s.upper() == 'VENCIDO':
        return None
    # ISO YYYY-MM-DD (con o sin hora)
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # DD/MM/YYYY
    if pd is not None:
        try:
            return pd.to_datetime(s, dayfirst=True).date()
        except Exception:
            pass
    return None


def normalize_cm(code):
    """Unifica códigos CM/MC: 'MC 01/2025' → 'MC01/25', 'CM01/25' → 'CM01/25'."""
    if not code:
        return None
    s = str(code).strip().upper().replace(' ', '')
    m = re.match(r'^(MC|CM)(\d+)/(\d{2,4})$', s)
    if m:
        prefix, num, year = m.group(1), m.group(2), m.group(3)
        if len(year) == 4:
            year = year[-2:]
        return f'{prefix}{num.zfill(2)}/{year}'
    return s


def extraer_chasis_de_texto(texto):
    """Extrae chasis de un texto tipo 'VITZ 2010 CHAS: KSP90-2010957' o
    'TOYOTA SIENTA 2004 CHASIS: NCP81-0029514'."""
    if not texto:
        return None
    m = re.search(r'CHASIS?\s*[N°:.\s]+([A-Z0-9\-]+)', str(texto).upper())
    if m:
        return m.group(1)
    m = re.search(r'CHAS[.:\s]+([A-Z0-9\-]+)', str(texto).upper())
    return m.group(1) if m else None


# ============================================================
#                  WORKFLOW DE BD (SAFE)
# ============================================================

def backup_db(db_path):
    """Hace backup nombrado con timestamp."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f'{db_path}.backup.pre_migracion_{timestamp}'
    shutil.copy2(db_path, backup_path)
    print(f'>> Backup: {backup_path}')
    return backup_path


def fresh_copy(src_db, dst_db='/tmp/w.db'):
    """Copia segura usando la backup API de SQLite (más robusto que cp en mounts)."""
    if os.path.exists(dst_db):
        os.remove(dst_db)
    src = sqlite3.connect(f'file:{src_db}?mode=ro&immutable=1', uri=True)
    dst = sqlite3.connect(dst_db)
    src.backup(dst)
    src.close()
    dst.close()
    # Verificar integridad
    c = sqlite3.connect(dst_db).cursor()
    c.execute('PRAGMA integrity_check')
    res = c.fetchone()[0]
    if res != 'ok':
        raise RuntimeError(f'Copia corrupta: {res}')
    return dst_db


def write_back(work_db, real_db):
    """Copia de vuelta con cat (más robusto que cp para mounts Windows)."""
    os.system(f'cat "{work_db}" > "{real_db}"')
    print(f'>> BD escrita a {real_db}')


def get_or_create(cur, table, search_kwargs, default_kwargs=None):
    """Helper genérico: busca un registro por search_kwargs. Si no existe lo crea
    con search + default. Devuelve el id."""
    where = ' AND '.join(f'{k}=?' for k in search_kwargs)
    cur.execute(f'SELECT id FROM {table} WHERE {where}', tuple(search_kwargs.values()))
    r = cur.fetchone()
    if r:
        return r[0]
    all_kwargs = {**search_kwargs, **(default_kwargs or {})}
    cols = ', '.join(all_kwargs.keys())
    placeholders = ', '.join(['?'] * len(all_kwargs))
    cur.execute(f'INSERT INTO {table} ({cols}) VALUES ({placeholders})', tuple(all_kwargs.values()))
    return cur.lastrowid


# ============================================================
#                  CONSTANTES DEL PROYECTO
# ============================================================

ENTERPRISE_ID = 3                # AUTO OFERTAS
BRANCH_CASA_CENTRAL = 1
BRANCH_SUCURSAL_1 = 2
PAY_CONTADO = 1
PAY_CREDITO = 3
PAY_MIXTO = 4

# Estructura típica de header del Excel anual de ventas:
VENTAS_COLS = {
    'cm':       0,
    'marca':    1,
    'modelo':   2,
    'color':    3,
    'year':     4,
    'chasis':   5,
    'fob':      6,   # PRECIO IQ (USD)
    'flete':    7,   # CIGÜEÑA (USD, puede ser compuesto)
    'despacho': 8,   # PYG
    'gas':      9,   # GAS APROX (PYG)
    'costo':    10,
    'precio':   11,  # PRECIO VENTA (PYG)
    'ganancia': 12,
    'condicion':13,  # CONTADO/CREDITO
    'fecha':    14,
}

MESES = ('ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO',
         'SETIEMBRE','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE')
