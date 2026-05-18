"""Tests del endpoint GET /api/cash-movements/export/.

Cubrimos:
  - BOM UTF-8 al inicio (para que Excel español muestre acentos).
  - Cabecera correcta y nombre de archivo coherente con el período.
  - Filtros: ?date_from/date_to y ?period=YYYY-MM (shortcut mensual).
  - Filtro por sucursal — no se filtran movimientos de otra sucursal.
  - Tenancy — un usuario no ve los movimientos de OTRA empresa.
  - Totales al final (INGRESOS / EGRESOS / NETO) coherentes con las filas.
  - Separador `,` cuando se pide ?delimiter=comma.
"""

from decimal import Decimal
from datetime import date

import pytest
from rest_framework.test import APIClient

from core.models import CustomUser, Enterprise, Branch, CashMovement


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    """Dos empresas con una sucursal cada una y movimientos de mayo+abril.

    La segunda empresa existe para verificar tenancy: lo que crea NO debe
    aparecer cuando el cliente del primer enterprise pide su CSV.
    """
    e1 = Enterprise.objects.create(
        name='E1', ruc='11111111', email='e1@test.com', phone='1', address='x', city='Asunción',
    )
    e2 = Enterprise.objects.create(
        name='E2', ruc='22222222', email='e2@test.com', phone='2', address='y', city='Asunción',
    )
    # Branch tiene unique (enterprise_id, code) — usamos codes distintos
    # para evitar el conflicto del default '' cuando hay dos sucursales
    # de la misma empresa.
    b1 = Branch.objects.create(enterprise=e1, name='Suc A', code='A')
    b1b = Branch.objects.create(enterprise=e1, name='Suc B', code='B')
    b2 = Branch.objects.create(enterprise=e2, name='Suc Otra', code='A')

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )

    # Mayo 2026 — empresa 1
    CashMovement.objects.create(
        enterprise=e1, branch=b1, date=date(2026, 5, 3),
        kind='venta_contado', direction='in', amount=Decimal('100000'),
        description='Venta contado mayo',
    )
    CashMovement.objects.create(
        enterprise=e1, branch=b1, date=date(2026, 5, 10),
        kind='alquiler', direction='out', amount=Decimal('30000'),
        description='Alquiler mayo',
    )
    CashMovement.objects.create(
        enterprise=e1, branch=b1b, date=date(2026, 5, 15),
        kind='cobro_cuota', direction='in', amount=Decimal('50000'),
        description='Cobro cuota — sucursal B',
    )

    # Abril 2026 — empresa 1 (NO debe aparecer si filtramos mayo)
    CashMovement.objects.create(
        enterprise=e1, branch=b1, date=date(2026, 4, 20),
        kind='gasto_playa', direction='out', amount=Decimal('5000'),
        description='Gasto abril',
    )

    # Empresa 2 — tenancy. Si el CSV de e1 trae este movimiento es bug grave.
    CashMovement.objects.create(
        enterprise=e2, branch=b2, date=date(2026, 5, 5),
        kind='venta_contado', direction='in', amount=Decimal('999999'),
        description='SECRETO de otra empresa',
    )

    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client, 'e1': e1, 'e2': e2, 'b1': b1, 'b1b': b1b, 'user': user}


def _decode_csv(response):
    """Devuelve (filas, raw_text). Pelamos el BOM si está presente."""
    raw = response.content.decode('utf-8')
    body = raw.lstrip('﻿')
    rows = [line for line in body.splitlines() if line != '']
    return rows, raw


def test_bom_y_content_type(setup):
    """El CSV debe arrancar con BOM UTF-8 y traer content-type text/csv."""
    r = setup['client'].get('/api/cash-movements/export/?period=2026-05')
    assert r.status_code == 200
    assert r.content.startswith('﻿'.encode('utf-8')), \
        'el CSV debe arrancar con BOM UTF-8 para que Excel ES muestre acentos'
    assert 'text/csv' in r['Content-Type']
    cd = r['Content-Disposition']
    assert 'flujo_caja_2026-05.csv' in cd


def test_period_filtra_mes_completo(setup):
    """?period=2026-05 debe traer sólo las 3 filas de mayo (no la de abril)."""
    r = setup['client'].get('/api/cash-movements/export/?period=2026-05')
    rows, _ = _decode_csv(r)
    # 1 header + 3 movimientos + 3 totales = 7
    assert len(rows) == 7, f'esperaba 7 filas, hay {len(rows)}\n{rows}'
    assert rows[0].startswith('Fecha;Sucursal;Tipo;Dirección'), \
        f'header inesperado: {rows[0]!r}'


def test_filtro_por_branch(setup):
    """?branch=b1 deja afuera los movimientos de b1b."""
    r = setup['client'].get(
        f'/api/cash-movements/export/?period=2026-05&branch={setup["b1"].id}'
    )
    rows, _ = _decode_csv(r)
    # 1 header + 2 movimientos (los 2 de Suc A) + 3 totales = 6
    assert len(rows) == 6
    body = '\n'.join(rows)
    assert 'Suc A' in body
    assert 'Suc B' not in body


def test_no_filtra_movimientos_de_otra_empresa(setup):
    """Tenancy: el CSV NUNCA debe traer movimientos de otra empresa."""
    r = setup['client'].get('/api/cash-movements/export/?period=2026-05')
    _, raw = _decode_csv(r)
    assert 'SECRETO' not in raw
    assert '999999' not in raw


def test_totales_coherentes(setup):
    """Las 3 últimas filas son TOTAL INGRESOS / EGRESOS / NETO."""
    r = setup['client'].get('/api/cash-movements/export/?period=2026-05')
    rows, _ = _decode_csv(r)
    # Las 3 últimas filas tienen los totales (van pegadas porque _decode_csv
    # filtró la línea en blanco).
    assert 'TOTAL INGRESOS' in rows[-3]
    assert '150000.00' in rows[-3]   # 100000 + 50000
    assert 'TOTAL EGRESOS' in rows[-2]
    assert '30000.00' in rows[-2]
    assert 'NETO' in rows[-1]
    assert '120000.00' in rows[-1]   # 150000 - 30000


def test_delimitador_coma(setup):
    """?delimiter=comma usa `,` en lugar de `;` (Excel internacional)."""
    r = setup['client'].get(
        '/api/cash-movements/export/?period=2026-05&delimiter=comma'
    )
    rows, _ = _decode_csv(r)
    assert rows[0].startswith('Fecha,Sucursal,Tipo,Dirección'), \
        f'header con coma esperado, got {rows[0]!r}'


def test_export_sin_filtros_no_explota(setup):
    """Sin filtros (caso "exportar todo"), responde 200 con un CSV válido."""
    r = setup['client'].get('/api/cash-movements/export/')
    assert r.status_code == 200
    rows, _ = _decode_csv(r)
    # header + 4 movimientos de e1 (mayo + abril) + 3 totales = 8
    assert len(rows) == 8


def test_filename_con_rango_explicito(setup):
    """date_from/date_to explícitos generan filename con el rango legible."""
    r = setup['client'].get(
        '/api/cash-movements/export/?date_from=2026-05-01&date_to=2026-05-31'
    )
    assert 'flujo_caja_2026-05-01_a_2026-05-31.csv' in r['Content-Disposition']
