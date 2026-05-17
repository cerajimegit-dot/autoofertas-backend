"""
Actualiza sale_date de las ventas 2026 matcheando por chasis (VIN) contra
'archivos_playa/VENTAS AUTO OFERTAS-CASA CENTRAL AÑO 2.026.ods'.

Uso (con el backend DETENIDO):
    python scripts/fix_sale_dates_2026.py              # modo dry-run
    python scripts/fix_sale_dates_2026.py --apply      # aplica cambios

Requiere: pandas, odfpy (pip install pandas odfpy)
"""

import os
import sys
import django
from pathlib import Path

# Permitir correr el script desde la raíz del proyecto
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

import pandas as pd
from datetime import datetime
from core.models import Sale


EXCEL = ROOT / 'archivos_playa' / 'VENTAS AUTO OFERTAS-CASA CENTRAL AÑO 2.026.ods'


def normaliza_vin(s):
    if s is None:
        return None
    return str(s).strip().upper().replace(' ', '')


def main():
    apply = '--apply' in sys.argv

    print(f"Leyendo {EXCEL.name}...")
    df = pd.read_excel(EXCEL, engine='odf', header=None)

    # El archivo tiene título en fila 0, encabezados en fila 1, header de mes en fila 2, datos desde fila 3+.
    # Columnas relevantes: 0=CON/INT, 5=CHASISS, 14=FECHA
    # Iteramos y descartamos filas-cabecera / vacías.

    actualizaciones = []  # (cm_code, chasis, fecha, sale_obj)
    saltadas = []

    for _, row in df.iterrows():
        cm = row[0]
        chasis_raw = row[5]
        fecha = row[14]
        if cm is None or pd.isna(cm):
            continue
        cm_str = str(cm).strip()
        # Descartar encabezados como "CON/INT", "ENERO 2.026", etc.
        if not cm_str or cm_str.upper() in ('CON/INT',) or cm_str.upper().startswith(('ENERO','FEBRERO','MARZO','ABRIL','MAYO','JUNIO','JULIO','AGOSTO','SETIEMBRE','SEPTIEMBRE','OCTUBRE','NOVIEMBRE','DICIEMBRE')):
            continue
        if pd.isna(fecha):
            saltadas.append((cm_str, 'sin fecha'))
            continue

        # Intentar encontrar la venta por CM code o por chasis
        vin = normaliza_vin(chasis_raw)
        qs = Sale.objects.filter(sale_number=cm_str)
        if not qs.exists() and vin:
            qs = Sale.objects.filter(vehicle__vin__iexact=vin)
        if not qs.exists():
            saltadas.append((cm_str, f'no match (vin={vin})'))
            continue

        # Parsear fecha
        if isinstance(fecha, datetime):
            new_date = fecha
        else:
            try:
                new_date = pd.to_datetime(fecha).to_pydatetime()
            except Exception:
                saltadas.append((cm_str, f'fecha no parseable: {fecha}'))
                continue

        for sale in qs:
            actualizaciones.append((cm_str, vin, new_date, sale))

    print(f"\n{len(actualizaciones)} ventas a actualizar:")
    for cm, vin, date, sale in actualizaciones[:10]:
        print(f"  {sale.sale_number:15}  VIN={vin or '-':20}  {sale.sale_date} -> {date.date()}")
    if len(actualizaciones) > 10:
        print(f"  ... y {len(actualizaciones)-10} más")

    print(f"\n{len(saltadas)} filas saltadas:")
    for cm, motivo in saltadas[:10]:
        print(f"  {cm}: {motivo}")

    if apply:
        print("\nAplicando cambios...")
        for _, _, new_date, sale in actualizaciones:
            sale.sale_date = new_date
            sale.save(update_fields=['sale_date'])
        print(f"✓ {len(actualizaciones)} ventas actualizadas.")
    else:
        print("\n(dry-run) Pasá --apply para aplicar los cambios.")


if __name__ == '__main__':
    main()
