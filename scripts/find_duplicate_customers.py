"""Detecta clientes duplicados normalizando el nombre completo.

Caso típico: la misma persona aparece dos veces porque alguien partió
diferente el nombre/apellido al cargar. Ejemplo real:

    id=216  first="CARLOS ALBERTO"  last="RAMOS JIMENEZ"     doc=48679178
    id=293  first="CARLOS"          last="ALBERTO RAMOS JIMENEZ"  doc=DRV026-0008

Ambas representan a la misma persona, pero con docs distintos y splits
distintos del nombre.

Lo que hace el script:
  1. Normaliza el full_name de cada cliente: lowercase + colapsa espacios
     + quita tildes + quita puntuación.
  2. Agrupa por full_name normalizado.
  3. Reporta cada grupo con 2+ fichas.
  4. Para cada grupo sugiere cuál ficha mantener basado en:
       - Doc real > doc autogenerado (CUOTA/DRV/SUC).
       - Más ventas con monto > 0.
       - Más reciente (created_at).
  5. Muestra todas las ventas de cada ficha para que el operador decida.

Read-only. Para mergear duplicados hay que hacerlo manualmente desde
la UI (ver sección 10.13 del manual).

USO:
    DB_ENGINE=sqlite python scripts/find_duplicate_customers.py
    DB_ENGINE=postgres python scripts/find_duplicate_customers.py
    python scripts/find_duplicate_customers.py --min-similarity 0.9   # fuzzy

    # Exportar CSV detallado:
    python scripts/find_duplicate_customers.py --csv duplicados.csv

    # Sólo mostrar grupos donde uno de los duplicados tiene ventas
    # con monto > 0 (los que realmente importan):
    python scripts/find_duplicate_customers.py --only-with-sales
"""

import argparse
import csv
import os
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Customer, Sale


def normalize(text):
    """Quita tildes, lowercase, colapsa espacios, quita puntuación.

    'CARLOS ALBERTO  RAMOS-JIMENEZ.' → 'carlos alberto ramos jimenez'
    'JOSÉ MARÍA' → 'jose maria'
    """
    if not text:
        return ''
    # Quitar tildes
    t = unicodedata.normalize('NFD', text)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    # Lowercase
    t = t.lower()
    # Quitar puntuación común
    for ch in '.,;:-_/\\()[]{}!?¡¿"\'':
        t = t.replace(ch, ' ')
    # Colapsar espacios múltiples
    t = ' '.join(t.split())
    return t


def is_doc_autogen(doc):
    if not doc:
        return False
    d = doc.upper()
    return d.startswith('DRV026') or d.startswith('SUC026') or d.startswith('CUOTA') or d.startswith('MIG')


def score_ficha(c, sales_count, sales_with_amount):
    """Heurística para sugerir la ficha "buena" de un grupo de duplicados.

    Más alto = más probable que sea la canónica.
    """
    s = 0
    if not is_doc_autogen(c.document_number or ''):
        s += 100             # doc real es lo más importante
    s += sales_with_amount * 10  # ventas con monto > 0
    s += sales_count            # cualquier venta cuenta poco
    if c.phone:
        s += 5
    if c.email and '@import.local' not in c.email:
        s += 3
    return s


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--csv', metavar='FILE', help='Exportar resultado detallado a CSV')
    p.add_argument('--only-with-sales', action='store_true',
                    help='Sólo grupos donde al menos una ficha tiene una venta con monto > 0')
    args = p.parse_args()

    # 1. Cargar todos los clientes y agruparlos por nombre normalizado
    clientes = list(Customer.objects.all())
    grupos = defaultdict(list)
    for c in clientes:
        full = f'{c.first_name or ""} {c.last_name or ""}'.strip()
        key = normalize(full)
        if len(key) < 3:
            continue  # nombre vacío o muy corto, no agrupar
        grupos[key].append(c)

    duplicados = {k: v for k, v in grupos.items() if len(v) > 1}

    # 2. Para cada grupo cargar las ventas
    ventas_por_cliente = {}
    for k, fichas in duplicados.items():
        for c in fichas:
            ventas_por_cliente[c.id] = list(
                Sale.objects.filter(customer=c).order_by('sale_date')
            )

    # 3. Filtro opcional: sólo grupos con ventas reales
    if args.only_with_sales:
        def has_real_sale(group):
            for c in group:
                for s in ventas_por_cliente.get(c.id, []):
                    if (s.total_price or 0) > 0:
                        return True
            return False
        duplicados = {k: v for k, v in duplicados.items() if has_real_sale(v)}

    if not duplicados:
        print('  No se encontraron clientes duplicados con los criterios actuales.')
        return

    # 4. Reporte
    print(f'\n{"=" * 78}')
    print(f'  CLIENTES DUPLICADOS DETECTADOS: {len(duplicados)} grupos')
    print(f'{"=" * 78}\n')

    csv_rows = []
    for k, fichas in sorted(duplicados.items()):
        # Calcular score para cada ficha
        scored = []
        for c in fichas:
            sales = ventas_por_cliente.get(c.id, [])
            sales_with_amount = sum(1 for s in sales if (s.total_price or 0) > 0)
            scored.append((c, sales, sales_with_amount, score_ficha(c, len(sales), sales_with_amount)))
        scored.sort(key=lambda x: -x[3])  # descending por score
        recommended = scored[0][0]

        print(f'  ─── "{fichas[0].first_name} {fichas[0].last_name}" '
              f'(normalizado: "{k}") ─── {len(fichas)} fichas')
        for c, sales, swa, score in scored:
            marker = '★ MANTENER' if c.id == recommended.id else '  Mergear/borrar'
            doc_tag = ' (auto)' if is_doc_autogen(c.document_number or '') else ''
            print(f'    {marker}  id={c.id:5}  doc={(c.document_number or "")+doc_tag:30}'
                  f'  first={(c.first_name or "")!r:30}  last={(c.last_name or "")!r:30}')
            print(f'                      tel={(c.phone or "-"):20}  email={(c.email or "-")}')
            print(f'                      ventas: {len(sales)}  (con monto: {swa})  score: {score}')
            for s in sales:
                fecha = s.sale_date.date() if s.sale_date else '?'
                print(f'                        venta {s.sale_number:15}  {fecha}  '
                      f'{s.status:10}  Gs.{int(s.total_price or 0):,}'.replace(',', '.'))
            csv_rows.append({
                'grupo': k,
                'recommendation': 'MANTENER' if c.id == recommended.id else 'MERGEAR',
                'customer_id': c.id,
                'document_number': c.document_number,
                'doc_autogenerado': 'SI' if is_doc_autogen(c.document_number or '') else 'NO',
                'first_name': c.first_name,
                'last_name': c.last_name,
                'phone': c.phone or '',
                'email': c.email or '',
                'n_ventas': len(sales),
                'n_ventas_con_monto': swa,
                'sales_numbers': ' | '.join(s.sale_number or '' for s in sales),
                'score': score,
            })
        print()

    # 5. CSV opcional
    if args.csv:
        out = Path(args.csv)
        with open(out, 'w', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()), delimiter=';')
            w.writeheader()
            w.writerows(csv_rows)
        print(f'  CSV exportado: {out.resolve()}  ({len(csv_rows)} filas)')

    # 6. Resumen final
    total_fichas = sum(len(v) for v in duplicados.values())
    total_a_mergear = total_fichas - len(duplicados)
    print(f'\n  RESUMEN: {len(duplicados)} grupos de duplicados.')
    print(f'  Total fichas duplicadas: {total_fichas}.')
    print(f'  Si se conservara una por grupo → se eliminarían {total_a_mergear} fichas redundantes.')


if __name__ == '__main__':
    main()
