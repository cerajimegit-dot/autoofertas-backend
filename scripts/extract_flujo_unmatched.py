"""Extrae las lineas "PAGO CUOTA" de un archivo de flujo de caja que el
script apply_flujo_caja.py no pudo matchear automaticamente.

Para cada linea sin match, calcula candidatos de Quotum que PODRIAN ser
la cuota referida (por amount + plan structure + fecha cercana), y los
exporta a un CSV que el Jr puede revisar.

OUTPUT: CSV con una fila por linea sin match, columnas:

  - file_row_id: identificador unico (1, 2, 3...)
  - fecha: fecha del flujo (DD/MM/YY)
  - amount: monto del cobro
  - quota_X: numero de cuota parseado del texto (X de "X/Y")
  - quota_Y: total del plan parseado del texto (Y de "X/Y")
  - cliente_anon: nombre del cliente OFUSCADO (Cliente_A, Cliente_B, ...)
  - reason: por que el script no pudo matchear
  - candidates_quota_ids: lista de Q ids candidatos (top 5)
  - candidates_detail: detalle de cada candidato

USO:
    DB_ENGINE=sqlite python scripts/extract_flujo_unmatched.py \
        "STOCK/junio2026/FLUJO DE CAJA MAYO 2.026 -.ods" \
        --out docs/jr/flujo_unmatched.csv
"""

import argparse
import csv
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Customer, Quotum


def fmt(n):
    return f'Gs.{int(n or 0):,}'.replace(',', '.')


def normalize(text):
    if not text:
        return ''
    t = unicodedata.normalize('NFD', text)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return t.upper().strip()


def parse_date(s):
    m = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', (s or '').strip())
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def parse_amount(s):
    if not s:
        return 0
    s2 = re.sub(r'[^\d]', '', s)
    return int(s2) if s2 else 0


def extract_rows(ods_path):
    """Devuelve una lista de filas (cada una es una lista de strings)."""
    NS_T = 'urn:oasis:names:tc:opendocument:xmlns:table:1.0'
    NS_TEXT = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'
    with zipfile.ZipFile(ods_path) as z:
        with z.open('content.xml') as f:
            xml = f.read().decode('utf-8', errors='replace')
    root = ET.fromstring(xml)
    sheets = root.findall(f'.//{{{NS_T}}}table')
    out = []
    if not sheets:
        return out
    for row in sheets[0].findall(f'{{{NS_T}}}table-row'):
        cells = []
        for cell in row.findall(f'{{{NS_T}}}table-cell'):
            repeated = cell.get(f'{{{NS_T}}}number-columns-repeated')
            texts = [t.text or '' for t in cell.iter(f'{{{NS_TEXT}}}p')]
            value = ' '.join(t.strip() for t in texts if t).strip()
            if repeated:
                try:
                    n = int(repeated)
                    if value:
                        cells.extend([value] * min(n, 10))
                    else:
                        cells.append('')
                except ValueError:
                    cells.append(value)
            else:
                cells.append(value)
        out.append(cells)
    return out


# Pattern: "PAGO CUOTA N° 10/24 SANDRA LORENA ALCARAZ"
QUOTA_PAT = re.compile(
    r'PAGO\s+CUOTA\s+N[°º]?\s*(\d+)(?:\s*[Yy]\s*(\d+))?/(\d+)\s+(.+?)(?:\s*\(OP\d+\))?$',
    re.IGNORECASE,
)


def anonymize_name(name, mapping):
    """Devuelve un nombre anonimo deterministico por nombre."""
    norm = normalize(name)
    if norm in mapping:
        return mapping[norm]
    n = len(mapping)
    # Genera "Cliente_A", "Cliente_B"... "Cliente_AA" cuando se acaben las letras
    letters = []
    x = n
    while True:
        letters.append(chr(ord('A') + (x % 26)))
        x //= 26
        if x == 0:
            break
    anon = 'Cliente_' + ''.join(reversed(letters))
    mapping[norm] = anon
    return anon


def find_customer_by_tokens(name_text, customers_cache):
    """Mismo algoritmo que apply_flujo_caja para reproducir el fallo."""
    norm = normalize(name_text)
    tokens = set(re.findall(r'[A-Z]{3,}', norm))
    GENERIC = {'DE', 'LA', 'LOS', 'DEL', 'SAN', 'EL', 'DA'}
    tokens -= GENERIC
    if not tokens:
        return None, 'sin tokens en el nombre'
    best = None
    best_score = 0
    multi = []
    for c, ctokens in customers_cache:
        overlap = len(tokens & ctokens)
        if overlap >= 2:
            if overlap > best_score:
                best_score = overlap
                best = c
                multi = [c]
            elif overlap == best_score:
                multi.append(c)
    if not best:
        return None, 'no encontre customer con >=2 tokens de overlap'
    if len(multi) > 1:
        return best, f'ambiguo ({len(multi)} customers con score {best_score})'
    return best, None


def candidate_quotas_for_amount_and_plan(amount, quota_n, total_plan, fecha,
                                          customer=None, also_paid=True):
    """Devuelve top-5 Quotum candidatos que matchearian este pago.

    Estrategia: empieza con filtros estrictos. Si no encuentra nada,
    va relajando. Esta variante INCLUYE cuotas paid por default (porque
    el caso comun es "ya esta paid sin CashMovement linkeado").

    Niveles de relajacion:
      1. customer + quota_X/Y + amount cercano +/- 5%
      2. customer + quota_X/Y (sin amount)
      3. customer + quota_X (sin Y)
      4. customer (todas sus cuotas)
    """
    base = Quotum.objects.select_related('sale', 'customer')
    if not also_paid:
        base = base.exclude(status__in=['paid', 'cancelled'])

    # Nivel 1: estricto
    qs = base
    if customer:
        qs = qs.filter(customer=customer)
    if quota_n:
        qs = qs.filter(quota_number=quota_n)
    if total_plan:
        qs = qs.filter(total_plan=total_plan)
    if amount > 0:
        # Tolerancia amplia (50%) por si el amount del flujo viene mal parseado
        amount_low = int(amount * 0.5)
        amount_high = int(amount * 1.5)
        qs_strict = qs.filter(amount__gte=amount_low, amount__lte=amount_high)
        if qs_strict.count() > 0:
            qs = qs_strict

    candidates = list(qs[:20])

    # Nivel 2: relajar plan
    if not candidates and customer and quota_n:
        qs = base.filter(customer=customer, quota_number=quota_n)
        candidates = list(qs[:20])

    # Nivel 3: customer + cualquier cuota
    if not candidates and customer:
        qs = base.filter(customer=customer)
        candidates = list(qs[:20])

    # Score
    scored = []
    for q in candidates:
        s = 0
        if customer and q.customer_id == customer.id:
            s += 100
        if quota_n and q.quota_number == quota_n:
            s += 30
        if total_plan and q.total_plan == total_plan:
            s += 20
        q_amt = int(q.amount or 0)
        if amount > 0 and abs(q_amt - amount) < 100:
            s += 25
        if fecha and q.due_date:
            d = abs((q.due_date - fecha).days)
            if d <= 7:
                s += 25
            elif d <= 30:
                s += 15
            elif d <= 60:
                s += 5
        if fecha and q.payment_date and q.payment_date == fecha:
            s += 50  # match perfecto de fecha de pago
        scored.append((s, q))
    scored.sort(key=lambda x: -x[0])
    return scored[:5]


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('ods_file', help='Ruta al archivo flujo .ods')
    p.add_argument('--out', default='docs/jr/flujo_unmatched.csv',
                    help='Donde guardar el CSV de trabajo del Jr')
    p.add_argument('--name-mapping-out', default='docs/jr/_name_mapping.csv',
                    help='Mapping nombre_real -> anonimo (queda con senior)')
    args = p.parse_args()

    ods_path = Path(args.ods_file)
    if not ods_path.exists():
        print(f'  No existe {ods_path}')
        return

    rows = extract_rows(ods_path)

    # Construir cache de customers (usando el mismo algoritmo que apply_flujo_caja)
    customers_cache = []
    for c in Customer.objects.all():
        full = normalize(f'{c.first_name or ""} {c.last_name or ""}')
        tokens = set(re.findall(r'[A-Z]{3,}', full))
        GENERIC = {'DE', 'LA', 'LOS', 'DEL', 'SAN', 'EL', 'DA'}
        tokens -= GENERIC
        customers_cache.append((c, tokens))

    # Iterar el archivo y juntar las que no matchean
    unmatched = []
    name_anon_map = {}

    fecha_actual = None
    for row in rows:
        # Detectar fecha en la primera celda numérica
        for cell in row[:3]:
            d = parse_date(cell)
            if d:
                fecha_actual = d
                break
        # Buscar PAGO CUOTA en cualquier celda
        for cell in row:
            m = QUOTA_PAT.search(cell or '')
            if not m:
                continue
            n1 = int(m.group(1))
            n2 = int(m.group(2)) if m.group(2) else None
            total = int(m.group(3))
            name_text = m.group(4).strip()

            # Buscar monto en la fila: tomar el cell con valor mas grande
            # (la fila del flujo tiene fecha + descripcion + ingreso/egreso + saldo;
            # el monto del pago es el mayor entre ingreso/egreso o saldo)
            amounts_in_row = []
            for c2 in row:
                a = parse_amount(c2)
                if a > 100000:  # cuotas son > 100k normalmente
                    amounts_in_row.append(a)
            # Si hay varios, tomamos el segundo mas grande (el primero suele ser
            # el saldo acumulado, el segundo el monto del movimiento)
            if len(amounts_in_row) >= 2:
                amounts_in_row.sort(reverse=True)
                amount = amounts_in_row[1]
            elif amounts_in_row:
                amount = amounts_in_row[0]
            else:
                amount = 0

            # Tratar de matchear el customer
            customer, reason = find_customer_by_tokens(name_text, customers_cache)

            # Asignar nombre anonimo PRIMERO para usarlo en el reason
            anon_name = anonymize_name(name_text, name_anon_map)

            # Si encontre customer pero no esta la quota X/Y unpaid -> recordar
            if customer and not reason:
                exists = Quotum.objects.filter(
                    customer=customer, quota_number=n1, total_plan=total,
                ).exclude(status__in=['paid', 'cancelled']).exists()
                if exists:
                    continue  # match exitoso, no es unmatched
                # Si X/Y existe pero ya esta paid, anotamos (con nombre ANONIMO)
                paid_exists = Quotum.objects.filter(
                    customer=customer, quota_number=n1, total_plan=total, status='paid',
                ).exists()
                if paid_exists:
                    reason = f'cuota {n1}/{total} de {anon_name} ya esta paid en BD'
                else:
                    reason = f'cuota {n1}/{total} no existe para {anon_name}'

            # Generar candidatos
            candidates = candidate_quotas_for_amount_and_plan(
                amount=amount, quota_n=n1, total_plan=total,
                fecha=fecha_actual, customer=customer,
            )
            # Si no hubo candidatos con quota_n filter, relajar y probar sin
            if not candidates:
                candidates = candidate_quotas_for_amount_and_plan(
                    amount=amount, quota_n=None, total_plan=None,
                    fecha=fecha_actual, customer=customer,
                )
            if not candidates and customer is None:
                # Sin customer, probamos solo amount + quota_n + total
                candidates = candidate_quotas_for_amount_and_plan(
                    amount=amount, quota_n=n1, total_plan=total,
                    fecha=fecha_actual, customer=None,
                )

            candidates_ids = ','.join(str(q.id) for _, q in candidates)
            candidates_detail = ' | '.join(
                f'Q#{q.id}(score={s},cust={q.customer_id},X/Y={q.quota_number}/{q.total_plan},'
                f'amt={int(q.amount or 0)},due={q.due_date},pay={q.payment_date},status={q.status})'
                for s, q in candidates
            )

            # Para el top candidato: verificar si ya tiene CashMovement asociado
            from core.models import CashMovement
            top_q = candidates[0][1] if candidates else None
            existing_cm_info = ''
            if top_q:
                existing_cms = CashMovement.objects.filter(
                    quota=top_q, kind='cobro_cuota',
                )
                if existing_cms.exists():
                    cm_first = existing_cms.first()
                    existing_cm_info = (
                        f'CM#{cm_first.id} date={cm_first.date} '
                        f'amount={int(cm_first.amount or 0)}'
                    )
                else:
                    existing_cm_info = 'NINGUN_CM_LINKEADO'

            unmatched.append({
                'fecha': fecha_actual.isoformat() if fecha_actual else '',
                'amount': amount,
                'quota_X': n1,
                'quota_X2': n2 or '',
                'quota_Y': total,
                'cliente_anon': anon_name,
                'reason': reason or 'unknown',
                'candidates_quota_ids': candidates_ids,
                'candidates_detail': candidates_detail,
                'top_candidate_cm_status': existing_cm_info,
            })
            break  # solo procesar una vez por fila

    if not unmatched:
        print('  No se encontraron lineas PAGO CUOTA sin match.')
        return

    # Escribir CSV de trabajo del Jr
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow([
            'file_row_id', 'fecha', 'amount', 'quota_X', 'quota_X2', 'quota_Y',
            'cliente_anon', 'reason',
            'candidates_quota_ids', 'candidates_detail',
            'top_candidate_cm_status',
            'jr_decision', 'jr_chosen_quota_id', 'jr_confidence', 'jr_notes',
        ])
        for i, row in enumerate(unmatched, start=1):
            w.writerow([
                i, row['fecha'], row['amount'],
                row['quota_X'], row['quota_X2'], row['quota_Y'],
                row['cliente_anon'], row['reason'],
                row['candidates_quota_ids'], row['candidates_detail'],
                row['top_candidate_cm_status'],
                '', '', '', '',  # columnas para que el Jr complete
            ])
    print(f'  CSV de trabajo del Jr: {out.resolve()}  ({len(unmatched)} filas)')

    # Escribir mapping nombre real -> anonimo (queda con senior)
    map_out = Path(args.name_mapping_out)
    map_out.parent.mkdir(parents=True, exist_ok=True)
    with open(map_out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['original_normalized', 'anon_name'])
        for k, v in name_anon_map.items():
            w.writerow([k, v])
    print(f'  Mapping nombre real -> anon: {map_out.resolve()}  (NO PASAR AL Jr)')
    print(f'\n  Para el Jr: solo pasale {out.name}')


if __name__ == '__main__':
    main()
