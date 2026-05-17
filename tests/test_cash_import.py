"""Tests del importador ODS de flujo de caja."""

import pytest
from datetime import date
from decimal import Decimal

from core.services.cash_import import (
    classify, parse_date_str, parse_amount, import_ods_to_cash_movements,
)
from core.models import CashMovement

pytestmark = pytest.mark.django_db


class TestClassify:
    """La heurística que mapea operación → kind."""

    @pytest.mark.parametrize('op,cond,expected', [
        # Cobros de cuota (cualquier formato)
        ('PAGO CUOTA N° 10/24 LUIS PEREZ', '',          'cobro_cuota'),
        ('PAGO CUOTA N 5/12 ALGUIEN',     '',           'cobro_cuota'),
        ('PAGO CUOTA N° 24/24 JUAN',      'CANCELADO',  'cobro_cuota'),
        # Ventas contado (la condición G manda)
        ('NEW VITZ 1.3CC 2011 CHA: X CLIENTE', 'CONTADO', 'venta_contado'),
        # Seña / crédito
        ('NEW VITZ 2008 CHA: X CLIENTE',       'CREDITO', 'seña_credito'),
        ('PAGO N° 1/1 X',                       'A/CUENTA','pago_a_cuenta'),
        # Egresos varios
        ('GASTOS PLAYA',                        '',        'gasto_playa'),
        ('PAGO DE ALQUILER FEBRERO/26',         '',        'alquiler'),
        ('AUTOCOM CANCELACION 5 UNID.',         'TC 6.600','compra_exterior'),
        ('AUTOWINI KIA SPORTAGE 2016',          'TC 6.600','compra_exterior'),
        ('DADANI (LENGUAZA)',                   '',        'compra_exterior'),
        ('LAYSOLA PAGO CIGÜEÑA 6 UNIDADES',     '',        'transporte'),
        ('DESPACHO 6 UNIDADES JAPON',           '',        'transporte'),
        # No clasificable
        ('Algo raro sin contexto',              '',        'otro'),
    ])
    def test_classify_keywords(self, op, cond, expected):
        assert classify(op, cond) == expected


class TestParsers:
    @pytest.mark.parametrize('s,expected', [
        ('02/02/26',   date(2026, 2, 2)),
        ('02/02/2026', date(2026, 2, 2)),
        ('2026-02-02', date(2026, 2, 2)),
        ('',           None),
        ('basura',     None),
    ])
    def test_parse_date_str(self, s, expected):
        assert parse_date_str(s) == expected

    @pytest.mark.parametrize('s,expected', [
        ('10000000',    Decimal('10000000')),
        ('-10000000',   Decimal('-10000000')),
        ('10.000.000',  Decimal('10000000')),   # separador de miles solo
        ('1.500,50',    Decimal('1500.50')),     # decimal con coma
        ('',            None),
        (None,          None),
    ])
    def test_parse_amount(self, s, expected):
        assert parse_amount(s) == expected


class TestImporter:
    """Importa un ODS de prueba creado al vuelo."""

    @pytest.fixture
    def sample_ods(self, tmp_path):
        """Crea un ODS con filas representativas del flujo real."""
        from odf.opendocument import OpenDocumentSpreadsheet
        from odf.table import Table, TableRow, TableCell
        from odf.text import P

        rows_data = [
            # (fecha, operación, monto, , , , condición)
            ('FLUJO DE CAJA AUTOOFERTAS', '', '', '', '', '', ''),
            ('FECHA', 'OPERACIÓN', 'MONTO', '', '', '', 'CONDICION'),
            # 1 cobro (debe saltar)
            ('02/02/26', 'PAGO CUOTA N° 10/24 LUIS PEREZ',     '1300000',   '', '', '', ''),
            # 1 venta contado (debe saltar)
            ('03/02/26', 'NEW VITZ 1.3CC CHA: X CLIENTE',      '46000000',  '', '', '', 'CONTADO'),
            # 1 seña (debe saltar)
            ('04/02/26', 'NEW VITZ 2008 CHA: X CLIENTE',       '10000000',  '', '', '', 'CREDITO'),
            # 1 alquiler (CREA)
            ('05/02/26', 'PAGO DE ALQUILER FEBRERO/26',         '-8400000', '', '', '', ''),
            # 1 gasto playa (CREA)
            ('05/02/26', 'GASTOS PLAYA',                        '-10000000','', '', '', ''),
            # 1 compra exterior USD con TC (CREA con currency=USD)
            ('06/02/26', 'AUTOCOM CANCELACION 5 UNID. TOTAL 15.521$', '-102438600', '', '', '', 'TC 6.600.-'),
            # 1 transporte (CREA)
            ('23/02/26', 'LAYSOLA CIGÜEÑA 6 UNIDADES',          '-16395480','', '', '', ''),
            # 1 fila inválida (sin fecha)
            ('',         'OBS: nota explicativa',               '',         '', '', '', ''),
        ]

        doc = OpenDocumentSpreadsheet()
        sheet = Table(name='Hoja1')
        for row_vals in rows_data:
            tr = TableRow()
            for v in row_vals:
                tc = TableCell()
                tc.addElement(P(text=str(v)))
                tr.addElement(tc)
            sheet.addElement(tr)
        doc.spreadsheet.addElement(sheet)

        path = tmp_path / 'flujo_test.ods'
        doc.save(str(path))
        return str(path)

    def test_import_skips_auto_creates_manual(
        self, sample_ods, test_enterprise, test_branch,
    ):
        result = import_ods_to_cash_movements(
            sample_ods, enterprise=test_enterprise, branch=test_branch,
        )

        # 3 filas son auto-tracked (cobro + contado + seña)
        assert result['skipped_auto'] == 3
        # 4 filas son manuales (alquiler + gasto + compra_exterior + transporte)
        assert result['created_manual'] == 4
        # 1 fila inválida (sin fecha)
        assert result['invalid_rows'] == 1
        # ninguna unclassified
        assert result['unclassified'] == []

        # Verificar que se crearon los 4 manuales con los kinds correctos
        manuals = CashMovement.objects.filter(
            enterprise=test_enterprise, is_auto=False,
        )
        assert manuals.count() == 4
        kinds = sorted(m.kind for m in manuals)
        assert kinds == ['alquiler', 'compra_exterior', 'gasto_playa', 'transporte']

    def test_import_detects_usd_and_tc(
        self, sample_ods, test_enterprise,
    ):
        import_ods_to_cash_movements(sample_ods, enterprise=test_enterprise)
        mov = CashMovement.objects.get(kind='compra_exterior')
        assert mov.currency == 'USD'
        assert mov.exchange_rate == Decimal('6600')
        # Extrajo 15.521 USD del texto "TOTAL 15.521$" — interpretado como
        # 15521 sin coma decimal (es el formato del Excel real)
        assert mov.amount_usd is not None
        assert mov.provider == 'AUTOCOM'

    def test_import_negative_amount_becomes_out_with_positive_amount(
        self, sample_ods, test_enterprise,
    ):
        import_ods_to_cash_movements(sample_ods, enterprise=test_enterprise)
        for m in CashMovement.objects.filter(is_auto=False):
            assert m.amount > 0, 'amount siempre positivo'
            assert m.direction == 'out', 'todos los manuales del sample son egresos'

    def test_import_dry_run_does_not_write(
        self, sample_ods, test_enterprise,
    ):
        result = import_ods_to_cash_movements(
            sample_ods, enterprise=test_enterprise, dry_run=True,
        )
        assert result['created_manual'] == 4
        # Pero no escribió
        assert CashMovement.objects.count() == 0

    def test_import_is_idempotent_safe(
        self, sample_ods, test_enterprise,
    ):
        """Correr 2 veces NO previene duplicados (es responsabilidad del
        usuario). Documentamos el comportamiento para que sea explícito."""
        import_ods_to_cash_movements(sample_ods, enterprise=test_enterprise)
        assert CashMovement.objects.filter(is_auto=False).count() == 4
        # Segunda corrida: duplica
        import_ods_to_cash_movements(sample_ods, enterprise=test_enterprise)
        assert CashMovement.objects.filter(is_auto=False).count() == 8
        # → Conclusión documentada: el importer es para un mes a la vez,
        #   borrar manualmente si se reimporta.
