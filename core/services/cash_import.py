"""Importador del archivo "FLUJO DE CAJA …".ods al modelo CashMovement.

Estrategia:
  - Los cobros, ventas contado y señas YA viven en el sistema (se generan
    automáticamente desde Sale y Quotum). Los detectamos y los SALTEAMOS:
    el dueño no necesita re-cargarlos.
  - Los gastos, alquileres, compras al exterior y transporte NO están en el
    sistema. Los CREAMOS como movimientos manuales (`is_auto=False`) con la
    descripción literal del Excel y la fecha original.
  - Las filas que no podemos clasificar las reportamos como "para revisar"
    para que un humano decida.

Para fechas ambiguas (`dd/mm/yy` con año de 2 dígitos) asumimos siglo 2000+.
"""

import re
from datetime import date, datetime
from decimal import Decimal

from core.models import CashMovement


# Palabras clave por categoría — heurística probada con el ODS de febrero.
KEYWORDS = [
    ('alquiler',        ['ALQUILER']),
    ('gasto_playa',     ['GASTOS PLAYA', 'GASTO PLAYA']),
    ('sueldo',          ['SUELDO', 'SALARIO']),
    ('comision',        ['COMISION', 'COMISIÓN', 'HONORARIO']),
    ('impuesto',        ['IMPUESTO', 'IVA', 'PATENTE', 'TIMBRADO']),
    ('transporte',      ['DESPACHO', 'CIGÜEÑA', 'CIGUEÑA', 'CIGUE', 'FLETE INTERNO']),
    ('compra_exterior', [
        'AUTOCOM', 'AUTOWINI', 'TURTOLA', 'DADANI', 'LAYSOLA',
        'COMPRA JAPON', 'COMPRA JAPÓN', 'COREA', 'IQI', 'IQ ',
    ]),
    # Auto-tracked (los detectamos para saltarlos):
    ('cobro_cuota',     ['PAGO CUOTA', 'PAGO DE CUOTA', 'CUOTA N']),
    ('venta_contado',   ['CONTADO']),  # se evalúa por la columna G también
    ('seña_credito',    ['SEÑA', 'SENA', 'CREDITO', 'CRÉDITO']),
]


def classify(operation_text: str, condicion: str = '') -> str:
    """Devuelve el `kind` apropiado para una operación dada.

    El parámetro `condicion` viene de la columna G del Excel
    (`CONTADO` / `CREDITO` / `CANCELADO` / `A/CUENTA` / `TC ...`).
    """
    op = (operation_text or '').upper()
    cond = (condicion or '').upper()

    # Prioridad: si dice PAGO CUOTA es cobro, sin importar la condición.
    if 'PAGO CUOTA' in op or 'CUOTA N' in op or 'CUOTA Nº' in op:
        return 'cobro_cuota'

    # Condición CONTADO en la columna G + monto positivo = venta contado.
    if 'CONTADO' in cond:
        return 'venta_contado'

    # Condición CREDITO en columna G = seña de crédito (lo que se cobra al firmar).
    if cond in ('CREDITO', 'CRÉDITO'):
        return 'seña_credito'

    # Condición A/CUENTA = pago a cuenta (no atado a cuota específica).
    if 'A/CUENTA' in cond or 'A CUENTA' in cond:
        return 'pago_a_cuenta'

    # Buscar por keywords en el texto de la operación.
    for kind, kws in KEYWORDS:
        for kw in kws:
            if kw in op:
                return kind

    return 'otro'


def parse_date_str(s) -> date | None:
    """Acepta '02/02/26' o '02/02/2026' o date(...) ya parseado."""
    if not s:
        return None
    if isinstance(s, date):
        return s
    s = str(s).strip()
    for fmt in ('%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(s) -> Decimal | None:
    """Acepta números o strings con/sin puntos de miles, posibles negativos."""
    if s is None or s == '':
        return None
    try:
        s = str(s).strip()
        # Heurísticas sobre el formato:
        # - "1.500,50": coma = decimal, puntos = miles.
        # - "10.000.000": múltiples puntos = todos son separadores de miles.
        # - "10000000": entero limpio.
        # - "1.5": un solo punto = decimal (Decimal lo acepta tal cual).
        if ',' in s:
            s = s.replace('.', '').replace(',', '.')
        elif s.count('.') > 1:
            s = s.replace('.', '')
        return Decimal(s)
    except Exception:
        return None


def read_ods_rows(file_path: str):
    """Devuelve una lista de dicts con las filas válidas del ODS.

    Cada dict: { 'date': date, 'op': str, 'amount': Decimal, 'condicion': str,
                 'extra': str, 'row_num': int }.
    Filas sin fecha o sin monto se reportan también como 'invalid' para
    que el caller pueda mostrarlas.
    """
    from odf.opendocument import load
    from odf.table import Table, TableRow, TableCell
    from odf.text import P

    def _cell_text(cell):
        parts = []
        for p in cell.getElementsByType(P):
            for child in p.childNodes:
                if hasattr(child, 'data'):
                    parts.append(child.data)
                elif hasattr(child, 'childNodes'):
                    for sub in child.childNodes:
                        if hasattr(sub, 'data'):
                            parts.append(sub.data)
        return ''.join(parts)

    def _cell_values(cell):
        repeated = int(cell.getAttribute('numbercolumnsrepeated') or 1)
        # Para celdas numéricas, ODS pone el valor en el atributo 'value'.
        val = cell.getAttribute('value') or _cell_text(cell)
        return [val] * repeated

    doc = load(file_path)
    rows_out = []
    for sheet in doc.spreadsheet.getElementsByType(Table):
        for i, row in enumerate(sheet.getElementsByType(TableRow), start=1):
            cells = []
            for cell in row.getElementsByType(TableCell):
                cells.extend(_cell_values(cell))
            # Stripear trailing vacíos
            while cells and not str(cells[-1]).strip():
                cells.pop()

            if len(cells) < 3:
                continue
            d = parse_date_str(cells[0])
            amount = parse_amount(cells[2])
            op = (cells[1] or '').strip()
            condicion = cells[6] if len(cells) > 6 else ''
            extra = cells[7] if len(cells) > 7 else ''

            rows_out.append({
                'row_num': i,
                'date': d,
                'op': op,
                'amount': amount,
                'condicion': str(condicion or '').strip(),
                'extra': str(extra or '').strip(),
                'valid': d is not None and amount is not None and op,
            })
    return rows_out


def import_ods_to_cash_movements(
    file_path: str,
    enterprise,
    branch=None,
    created_by=None,
    dry_run: bool = False,
):
    """Importa el ODS y crea CashMovement para los gastos/compras manuales.

    Saltea los movimientos cuyo `kind` resuelve a auto-tracked (cobros,
    ventas contado, señas) — esos ya viven en el sistema desde Sale/Quotum.

    Devuelve un dict con resumen:
        {
            'total_rows': int,
            'invalid_rows': int,
            'skipped_auto': int,    # ya en el sistema
            'created_manual': int,  # gastos/compras cargados ahora
            'unclassified': [{...}, ...],  # filas a revisar a mano
            'created': [{...}],     # detalle de lo creado (sólo si dry-run)
        }
    """
    rows = read_ods_rows(file_path)
    invalid = [r for r in rows if not r['valid']]
    valid = [r for r in rows if r['valid']]

    skipped_auto = 0
    created_manual = 0
    unclassified = []
    created_details = []
    to_create = []

    AUTO_TRACKED = {'cobro_cuota', 'venta_contado', 'seña_credito', 'pago_a_cuenta'}

    for r in valid:
        kind = classify(r['op'], r['condicion'])

        if kind in AUTO_TRACKED:
            # Ya viven en el sistema automáticamente.
            skipped_auto += 1
            continue

        # Detectar moneda: si el `extra` o `condicion` contiene "TC NNNN", es USD.
        currency = 'PYG'
        exchange_rate = None
        amount_usd = None
        tc_match = re.search(r'TC[\.\s]*(\d[\d.]*)', r['condicion'] + ' ' + r['extra'])
        if tc_match:
            tc_str = tc_match.group(1).replace('.', '')
            try:
                exchange_rate = Decimal(tc_str)
                currency = 'USD'
                # Tratar de extraer el USD del texto de la operación (ej "8.736$" o "TOTAL 15.521$")
                usd_match = re.search(r'TOTAL\s*([\d\.,]+)\s*\$', r['op'])
                if not usd_match:
                    usd_match = re.search(r'(\d[\d\.,]*)\s*\$', r['op'])
                if usd_match:
                    s = usd_match.group(1)
                    if ',' in s: s = s.replace('.', '').replace(',', '.')
                    try: amount_usd = Decimal(s)
                    except Exception: amount_usd = None
            except Exception:
                pass

        amount_abs = abs(r['amount'])
        direction = 'out' if r['amount'] < 0 else 'in'

        # Detectar proveedor en el texto (primer keyword conocido).
        provider = ''
        for kw in ('AUTOCOM', 'AUTOWINI', 'TURTOLA', 'DADANI', 'LAYSOLA'):
            if kw in r['op'].upper():
                provider = kw
                break

        if kind == 'otro':
            unclassified.append({
                'row': r['row_num'], 'date': r['date'].isoformat(),
                'op': r['op'], 'amount': float(r['amount']),
            })
            # Igual lo creamos como 'otro' para no perderlo.

        mov = CashMovement(
            enterprise=enterprise, branch=branch,
            date=r['date'], kind=kind, direction=direction,
            amount=amount_abs, currency=currency,
            amount_usd=amount_usd, exchange_rate=exchange_rate,
            description=r['op'],
            provider=provider,
            is_auto=False,
            created_by=created_by,
            notes=f'Importado de ODS — fila {r["row_num"]}',
        )
        to_create.append(mov)
        created_details.append({
            'date': r['date'].isoformat(), 'kind': kind, 'direction': direction,
            'amount': float(amount_abs), 'op': r['op'][:60],
        })
        created_manual += 1

    if not dry_run and to_create:
        CashMovement.objects.bulk_create(to_create, batch_size=200)

    return {
        'total_rows': len(rows),
        'invalid_rows': len(invalid),
        'skipped_auto': skipped_auto,
        'created_manual': created_manual,
        'unclassified': unclassified,
        'created': created_details,
    }
