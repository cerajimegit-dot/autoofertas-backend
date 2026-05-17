"""
Recupera las fechas reales de venta desde dos fuentes:
  1. stock.db       -> BD del sistema anterior (ventas 2022-2024)
  2. VENTAS...ods   -> Excel de ventas 2026

Estrategia de match (en orden, se toma el PRIMERO que encuentra):
  1. Por código interno: old.codigo_interno == sale.sale_number
  2. Por chasis/VIN normalizado (sin espacios, ceros a la izq, ni sufijo .0)

Uso (con el backend DETENIDO):
    python scripts/fix_sale_dates.py               # dry-run
    python scripts/fix_sale_dates.py --apply       # aplica cambios
"""

import os
import re
import sys
import sqlite3
import django
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

import pandas as pd
from core.models import Sale


STOCK_DB = ROOT / 'stock.db'
EXCEL_2026 = ROOT / 'archivos_playa' / 'VENTAS AUTO OFERTAS-CASA CENTRAL AÑO 2.026.ods'


def normaliza_vin(raw):
    """Normaliza VINs para comparar entre sistemas.

    Ej: ' 002099 '      -> '2099'
        '822903.0'      -> '822903'
        'ABC-123/XZ'    -> 'ABC123XZ'
    """
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if not s or s in ('NAN', 'NONE'):
        return None
    # Quitar el sufijo .0 que dejó float->str
    if re.match(r'^\d+\.0+$', s):
        s = s.split('.')[0]
    # Quitar caracteres no alfanuméricos
    s = re.sub(r'[^A-Z0-9]', '', s)
    # Quitar ceros a la izquierda
    s = s.lstrip('0') or s
    return s or None


def read_old_system():
    """Devuelve lista de dicts: {codigo, vin_norm, fecha, fuente}"""
    out = []
    if not STOCK_DB.exists():
        print(f"(!) No se encontró {STOCK_DB.name}, salteando fuente 1")
        return out
    conn = sqlite3.connect(STOCK_DB)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT v.codigo_interno, v.fecha, p.numero_chasis
            FROM venta v LEFT JOIN producto p ON v.producto_id = p.id
            WHERE v.fecha IS NOT NULL
        """)
        for codigo, fecha, chasis in cur.fetchall():
            try:
                parsed = pd.to_datetime(fecha).to_pydatetime()
            except Exception:
                continue
            out.append({
                'codigo': (codigo or '').strip() or None,
                'vin_norm': normaliza_vin(chasis),
                'fecha': parsed,
                'fuente': 'stock.db',
            })
    finally:
        conn.close()
    print(f"  stock.db: {len(out)} registros con fecha")
    return out


def read_excel_2026():
    """Devuelve lista de dicts: {codigo, vin_norm, fecha, fuente}"""
    out = []
    if not EXCEL_2026.exists():
        print(f"(!) No se encontró {EXCEL_2026.name}, salteando fuente 2")
        return out
    try:
        df = pd.read_excel(EXCEL_2026, engine='odf', header=None)
    except Exception as e:
        print(f"(!) Error leyendo {EXCEL_2026.name}: {e}")
        return out

    # Columnas: 0=CON/INT (CM code), 5=CHASISS, 14=FECHA
    meses = (
        'ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO',
        'AGOSTO', 'SETIEMBRE', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE'
    )
    for _, row in df.iterrows():
        cm = row[0]
        chasis = row[5]
        fecha = row[14]
        if cm is None or pd.isna(cm):
            continue
        cm_str = str(cm).strip()
        if not cm_str or cm_str.upper() == 'CON/INT' or cm_str.upper().startswith(meses):
            continue
        if pd.isna(fecha):
            continue
        try:
            parsed = (
                fecha if isinstance(fecha, datetime)
                else pd.to_datetime(fecha).to_pydatetime()
            )
        except Exception:
            continue
        out.append({
            'codigo': cm_str,
            'vin_norm': normaliza_vin(chasis),
            'fecha': parsed,
            'fuente': 'excel_2026',
        })
    print(f"  excel 2026: {len(out)} registros con fecha")
    return out


def main():
    apply = '--apply' in sys.argv

    print("==== Leyendo fuentes ====")
    source_data = read_old_system() + read_excel_2026()

    # Construir índices
    by_code = {}   # codigo -> fecha (último gana)
    by_vin = {}    # vin_norm -> fecha
    for d in source_data:
        if d['codigo']:
            by_code[d['codigo'].upper()] = d
        if d['vin_norm']:
            by_vin[d['vin_norm']] = d

    print(f"\nÍndices construidos: {len(by_code)} por código, {len(by_vin)} por chasis")

    print("\n==== Procesando ventas actuales ====")
    actualizaciones = []      # (sale, old_date, new_date, fuente, criterio)
    sin_match = []

    sales = Sale.objects.select_related('vehicle').all()
    for sale in sales:
        match = None
        criterio = None

        # 1) por código
        if sale.sale_number:
            m = by_code.get(sale.sale_number.upper())
            if m:
                match = m
                criterio = 'código'

        # 2) por VIN
        if not match and sale.vehicle and sale.vehicle.vin:
            vin_norm = normaliza_vin(sale.vehicle.vin)
            if vin_norm:
                m = by_vin.get(vin_norm)
                if m:
                    match = m
                    criterio = 'chasis'

        if not match:
            sin_match.append(sale)
            continue

        new_date = match['fecha']
        if sale.sale_date and sale.sale_date.date() == new_date.date():
            continue  # ya está correcta

        actualizaciones.append((sale, sale.sale_date, new_date, match['fuente'], criterio))

    print(f"\n{len(actualizaciones)} ventas a actualizar")
    print(f"{len(sin_match)} ventas SIN match (quedan con la fecha actual)")

    # Mostrar muestra
    if actualizaciones:
        print("\n--- Muestra (primeras 15) ---")
        for sale, old, new, fuente, crit in actualizaciones[:15]:
            old_s = old.strftime('%Y-%m-%d') if old else '-'
            print(f"  {sale.sale_number:15}  {old_s} -> {new.strftime('%Y-%m-%d')}  ({fuente}, match por {crit})")

    # Desglose por fuente
    from collections import Counter
    by_src = Counter((u[3], u[4]) for u in actualizaciones)
    print("\n--- Desglose ---")
    for (fuente, crit), cnt in sorted(by_src.items()):
        print(f"  {fuente:12} via {crit:8}: {cnt}")

    # Algunas sin match para debug
    if sin_match:
        print(f"\n--- Muestra SIN match (primeras 10) ---")
        for sale in sin_match[:10]:
            vin = sale.vehicle.vin if sale.vehicle else '-'
            print(f"  {sale.sale_number:15}  VIN={vin!r:20}  fecha actual={sale.sale_date}")

    if apply:
        print("\n==== Aplicando cambios ====")
        for sale, _, new_date, _, _ in actualizaciones:
            sale.sale_date = new_date
            sale.save(update_fields=['sale_date'])
        print(f"✓ {len(actualizaciones)} ventas actualizadas.")
    else:
        print("\n(dry-run). Corré con --apply para aplicar los cambios.")


if __name__ == '__main__':
    main()
