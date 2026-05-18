"""Análisis de la cartera vencida — identifica patrones de "data basura".

Marcelo notó que el monto de cartera vencida en el dashboard parece muy
alto. Este script revisa las cuotas vencidas desde varios ángulos para
detectar:

  - Clientes con docs autogenerados por la migración (no sabemos quiénes son).
  - Cuotas vencidas hace mucho tiempo (>2 años; típicamente ya cobradas
    fuera del sistema pero nunca marcadas).
  - Cuotas asociadas a ventas con código MIG (importadas).
  - Cuotas que ya no deberían contar (venta cancelada, etc.).

Salida:
  - Resumen ejecutivo en stdout.
  - CSV detallado en docs/reports/cartera_vencida.csv para que rocío
    pueda filtrar y depurar a mano.

USO:
    DB_ENGINE=sqlite python scripts/analyze_cartera_vencida.py
"""

import csv
import os
import sys
from datetime import date
from pathlib import Path

# Permitir correr el script desde scripts/ — agrega la raíz del repo al path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from django.db.models import Sum, Count, Q
from core.models import Quotum, Sale, Customer

TODAY = date.today()
ROOT = Path(__file__).parent.parent
REPORTS = ROOT / 'docs' / 'reports'
REPORTS.mkdir(parents=True, exist_ok=True)


def section(title):
    print(f'\n{"=" * 70}\n  {title}\n{"=" * 70}')


def fmt(n):
    return f'Gs. {int(n or 0):,}'.replace(',', '.')


# Base: cuotas vencidas (due_date pasado, no pagadas, no canceladas).
vencidas = Quotum.objects.filter(
    due_date__lt=TODAY,
).exclude(status__in=['paid', 'cancelled'])


section('1. Resumen general')
total_vencidas = vencidas.count()
total_monto = vencidas.aggregate(s=Sum('amount'))['s'] or 0
print(f'  Cuotas vencidas:     {total_vencidas:,}'.replace(',', '.'))
print(f'  Monto total:         {fmt(total_monto)}')
print(f'  Clientes únicos:     {vencidas.values("customer_id").distinct().count()}')
print(f'  Ventas únicas:       {vencidas.values("sale_id").distinct().count()}')


section('2. Distribución por antigüedad de la deuda')
buckets = [
    ('1-30 días',     1,    30,   '🟢'),
    ('31-90 días',    31,   90,   '🟡'),
    ('91-180 días',   91,   180,  '🟠'),
    ('181-365 días',  181,  365,  '🔴'),
    ('1-2 años',      366,  730,  '⚫'),
    ('2-5 años',      731,  1825, '☠'),
    ('+5 años',       1826, 99999, '🪦'),
]
for label, low, high, emoji in buckets:
    qs = vencidas.extra(
        where=[f"julianday('now') - julianday(due_date) BETWEEN {low} AND {high}"]
    )
    n = qs.count()
    m = qs.aggregate(s=Sum('amount'))['s'] or 0
    pct_n = n / total_vencidas * 100 if total_vencidas else 0
    pct_m = float(m) / float(total_monto) * 100 if total_monto else 0
    print(f'  {emoji} {label:14}  {n:5,}  ({pct_n:5.1f}%)  {fmt(m):>20}  ({pct_m:5.1f}%)'.replace(',', '.'))


section('3. Cuotas vencidas con cliente de doc autogenerado (migración)')
# Docs tipo DRV026-XXXX, SUC026-XXXX, CUOTA-XXXX
auto_docs = Q(customer__document_number__startswith='DRV026') | \
            Q(customer__document_number__startswith='SUC026') | \
            Q(customer__document_number__istartswith='CUOTA')
auto_vencidas = vencidas.filter(auto_docs)
n_auto = auto_vencidas.count()
m_auto = auto_vencidas.aggregate(s=Sum('amount'))['s'] or 0
print(f'  Cuotas:              {n_auto:,}'.replace(',', '.'))
print(f'  Monto:               {fmt(m_auto)} ({float(m_auto)/float(total_monto)*100:.1f}% del total vencido)')
print(f'  Clientes:            {auto_vencidas.values("customer_id").distinct().count()}')
print()
print('  Sub-distribución por prefijo:')
for prefix in ['DRV026', 'SUC026', 'CUOTA']:
    if prefix == 'CUOTA':
        sub = vencidas.filter(customer__document_number__istartswith='CUOTA')
    else:
        sub = vencidas.filter(customer__document_number__startswith=prefix)
    print(f'    {prefix:8}  {sub.count():4,} cuotas  {fmt(sub.aggregate(s=Sum("amount"))["s"]):>20}'.replace(',', '.'))


section('4. Cuotas vencidas de ventas con código MIG')
mig_vencidas = vencidas.filter(sale__sale_number__istartswith='MIG')
n_mig = mig_vencidas.count()
m_mig = mig_vencidas.aggregate(s=Sum('amount'))['s'] or 0
print(f'  Cuotas:              {n_mig:,}'.replace(',', '.'))
print(f'  Monto:               {fmt(m_mig)} ({float(m_mig)/float(total_monto)*100:.1f}% del total vencido)')


section('5. Cuotas vencidas asociadas a ventas canceladas (INCONSISTENCIA)')
canceladas = vencidas.filter(sale__status='cancelled')
print(f'  Cuotas:              {canceladas.count():,}'.replace(',', '.'))
print(f'  Monto:               {fmt(canceladas.aggregate(s=Sum("amount"))["s"])}')
if canceladas.exists():
    print('  ⚠ Estas cuotas no deberían estar pendientes — la venta está cancelada.')
    print('  Sugerencia: cancelar las cuotas o reabrir la venta si fue error.')


section('6. Cuotas vencidas con monto 0 o NULL')
basura = vencidas.filter(Q(amount=0) | Q(amount__isnull=True))
print(f'  Cuotas:              {basura.count():,}'.replace(',', '.'))
if basura.exists():
    print('  Sugerencia: borrarlas — no cobrarles algo de monto 0.')


section('7. Top 30 clientes por monto vencido')
top = (
    Customer.objects
    .filter(quotas__in=vencidas)
    .annotate(
        n_vencidas=Count('quotas', filter=Q(quotas__id__in=vencidas)),
        m_vencido=Sum('quotas__amount', filter=Q(quotas__id__in=vencidas)),
    )
    .order_by('-m_vencido')[:30]
)
print(f'  {"#":>3}  {"Cliente":40}  {"Doc":20}  {"Vencidas":>9}  {"Monto":>18}  Categoría')
print(f'  {"-"*3}  {"-"*40}  {"-"*20}  {"-"*9}  {"-"*18}  {"-"*30}')
for i, c in enumerate(top, 1):
    nombre = f'{c.first_name or ""} {c.last_name or ""}'.strip()[:40]
    doc = (c.document_number or '')[:20]
    # Categoría rápida
    if doc.startswith('DRV026'):
        cat = '⚠ Doc DRV (migración)'
    elif doc.startswith('SUC026'):
        cat = '⚠ Doc SUC (migración)'
    elif doc.upper().startswith('CUOTA'):
        cat = '⚠ Doc CUOTA (migración)'
    else:
        cat = ''
    print(f'  {i:>3}  {nombre:40}  {doc:20}  {c.n_vencidas:>9,}  {fmt(c.m_vencido):>18}  {cat}'.replace(',', '.'))


section('8. CSV detallado guardado en docs/reports/')
out_csv = REPORTS / 'cartera_vencida.csv'
with open(out_csv, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow([
        'Cliente_ID', 'Cliente_Nombre', 'Documento', 'Doc_autogenerado',
        'Telefono', 'Email',
        'Venta_Numero', 'Venta_Estado', 'Es_MIG',
        'Cuota_Numero', 'Plan', 'Monto', 'Fecha_Venc', 'Dias_atraso',
        'Estado_Cuota',
    ])
    qs = vencidas.select_related('customer', 'sale').order_by('-amount')
    for q in qs:
        c = q.customer
        s = q.sale
        doc = (c.document_number or '') if c else ''
        is_auto = bool(
            doc.startswith('DRV026') or doc.startswith('SUC026') or doc.upper().startswith('CUOTA')
        )
        is_mig = bool(s and (s.sale_number or '').upper().startswith('MIG'))
        dias = (TODAY - q.due_date).days if q.due_date else 0
        w.writerow([
            c.id if c else '',
            (f'{c.first_name or ""} {c.last_name or ""}'.strip()) if c else '',
            doc,
            'SI' if is_auto else 'NO',
            (c.phone or '') if c else '',
            (c.email or '') if c else '',
            s.sale_number if s else '',
            s.status if s else '',
            'SI' if is_mig else 'NO',
            q.quota_number,
            q.plan_name or '',
            int(q.amount or 0),
            q.due_date.isoformat() if q.due_date else '',
            dias,
            q.status,
        ])
print(f'  Archivo:             {out_csv}')
print(f'  Filas:               {vencidas.count():,}'.replace(',', '.'))
print('  Columnas: Cliente, Doc, Auto?, Tel, Email, Venta, EstadoVenta, MIG?,')
print('            Cuota#, Plan, Monto, Vence, DíasAtraso, EstadoCuota')


section('9. Conclusiones rápidas')
sospechosas_total = (
    auto_vencidas.aggregate(s=Sum('amount'))['s'] or 0
)
print(f'  Cuotas de docs autogenerados:       {fmt(sospechosas_total)} ({float(sospechosas_total)/float(total_monto)*100:.1f}% del total)')
print(f'  Cuotas de ventas MIG:               {fmt(m_mig)} ({float(m_mig)/float(total_monto)*100:.1f}%)')
print(f'  Cuotas de ventas canceladas:        {fmt(canceladas.aggregate(s=Sum("amount"))["s"] or 0)}')
print(f'  Cuotas con monto 0:                 {basura.count()}')
print()
print(f'  Si se depuran las "sospechosas" la cartera vencida pasaría de')
print(f'  {fmt(total_monto)} a aprox. {fmt(total_monto - sospechosas_total - m_mig)} (estimación gruesa,')
print(f'  porque hay overlap entre categorías).')
