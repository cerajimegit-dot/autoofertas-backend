"""Tests para Sale.collection_status — estado de cobranza calculado dinámicamente.

Cubre el bug reportado: ventas marcadas como "Completada" en el listado pero
con cuotas pendientes pasaban desapercibidas. Ahora `status='completed'`
significa "contrato cerrado" y `collection_status` muestra qué tan cobrada
está realmente.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal

from core.models import (
    Brand, VehicleModel, Vehicle, Customer, PaymentForm, Sale, Quotum,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_basic(test_enterprise, test_branch):
    brand = Brand.objects.create(enterprise=test_enterprise, name='Toyota')
    model = VehicleModel.objects.create(
        enterprise=test_enterprise, brand=brand, name='Vitz',
    )
    customer = Customer.objects.create(
        enterprise=test_enterprise, first_name='X', last_name='Y',
        document_number='9999',
    )
    return {
        'enterprise': test_enterprise,
        'branch': test_branch,
        'brand': brand,
        'model': model,
        'customer': customer,
    }


@pytest.fixture
def make_vehicle(setup_basic):
    n = {'i': 0}
    def _f():
        n['i'] += 1
        return Vehicle.objects.create(
            enterprise=setup_basic['enterprise'], branch=setup_basic['branch'],
            brand=setup_basic['brand'], model=setup_basic['model'], year=2018,
            vin=f'VINCOLL{n["i"]:03d}', price=Decimal('10000000'),
            fob=Decimal('0'), container=Decimal('0'),
            dispatch=Decimal('0'), cam_vol=Decimal('0'),
            state='available',
        )
    return _f


@pytest.fixture
def credito(test_enterprise):
    return PaymentForm.objects.create(enterprise=test_enterprise, name='CREDITO')


@pytest.fixture
def contado(test_enterprise):
    return PaymentForm.objects.create(enterprise=test_enterprise, name='CONTADO')


def _make_sale(setup, vehicle, pf, sale_number, status='completed', total=10_000_000):
    return Sale.objects.create(
        enterprise=setup['enterprise'], branch=setup['branch'],
        sale_number=sale_number, customer=setup['customer'], vehicle=vehicle,
        unit_price=Decimal(str(total)), total_price=Decimal(str(total)),
        payment_form=pf, status=status,
    )


def _make_q(sale, n, due_date, status='pending', amount=500_000):
    return Quotum.objects.create(
        enterprise=sale.enterprise, sale=sale, customer=sale.customer,
        quota_number=n, total_plan=24,
        amount=Decimal(str(amount)), due_date=due_date, status=status,
    )


class TestCollectionStatus:

    def test_cm_36_26_scenario_credit_with_pending_quotas_is_unpaid(
        self, setup_basic, make_vehicle, credito,
    ):
        """CM36/26 real: completed + crédito + 24 cuotas pending, 0 cobradas.
        Antes mostraba 'Completada' a secas. Ahora collection_status='unpaid'."""
        sale = _make_sale(setup_basic, make_vehicle(), credito, 'CM36/26')
        for i in range(1, 25):
            _make_q(sale, i, date.today() + timedelta(days=30 * i))
        assert sale.collection_status == 'unpaid'
        s = sale.collection_summary
        assert s['n_total'] == 24
        assert s['n_paid'] == 0
        assert s['balance_pending'] == 12_000_000  # 24 * 500k

    def test_cash_sale_completed_is_paid_full(
        self, setup_basic, make_vehicle, contado,
    ):
        sale = _make_sale(setup_basic, make_vehicle(), contado, 'C/26')
        assert sale.collection_status == 'paid_full'

    def test_credit_sale_with_some_paid_is_collecting(
        self, setup_basic, make_vehicle, credito,
    ):
        sale = _make_sale(setup_basic, make_vehicle(), credito, 'CR/26')
        # 3 pagas, 21 pending — todas futuras (no overdue)
        for i in range(1, 4):
            _make_q(sale, i, date.today() - timedelta(days=10), status='paid')
        for i in range(4, 25):
            _make_q(sale, i, date.today() + timedelta(days=30 * i))
        assert sale.collection_status == 'collecting'
        assert sale.collection_summary['n_paid'] == 3
        assert sale.collection_summary['n_total'] == 24

    def test_credit_sale_all_paid_is_paid_full(
        self, setup_basic, make_vehicle, credito,
    ):
        sale = _make_sale(setup_basic, make_vehicle(), credito, 'AP/26')
        for i in range(1, 25):
            _make_q(sale, i, date.today() - timedelta(days=10), status='paid')
        assert sale.collection_status == 'paid_full'

    def test_credit_sale_with_overdue_quota_is_overdue(
        self, setup_basic, make_vehicle, credito,
    ):
        sale = _make_sale(setup_basic, make_vehicle(), credito, 'O/26')
        _make_q(sale, 1, date.today() - timedelta(days=30), status='pending')  # vencida
        _make_q(sale, 2, date.today() + timedelta(days=30))
        assert sale.collection_status == 'overdue'

    def test_credit_sale_with_legacy_overdue_status(
        self, setup_basic, make_vehicle, credito,
    ):
        sale = _make_sale(setup_basic, make_vehicle(), credito, 'OL/26')
        _make_q(sale, 1, date.today() - timedelta(days=30), status='overdue')  # legacy
        _make_q(sale, 2, date.today() + timedelta(days=30))
        assert sale.collection_status == 'overdue'

    def test_cancelled_sale_is_cancelled(
        self, setup_basic, make_vehicle, credito,
    ):
        sale = _make_sale(setup_basic, make_vehicle(), credito, 'X/26', status='cancelled')
        _make_q(sale, 1, date.today() - timedelta(days=10), status='paid')
        # Aun con una cuota pagada, una venta cancelada se muestra cancelada
        assert sale.collection_status == 'cancelled'

    def test_sale_without_quotas_and_not_contado_is_no_plan(
        self, setup_basic, make_vehicle, credito,
    ):
        sale = _make_sale(setup_basic, make_vehicle(), credito, 'NP/26')
        assert sale.collection_status == 'no_plan'

    def test_status_display_renames_completed_to_cerrada(
        self, setup_basic, make_vehicle, credito,
    ):
        sale = _make_sale(setup_basic, make_vehicle(), credito, 'D/26')
        assert sale.get_status_display() == 'Cerrada'

    def test_status_display_renames_pending_to_reserva(
        self, setup_basic, make_vehicle, credito,
    ):
        sale = _make_sale(setup_basic, make_vehicle(), credito, 'R/26', status='pending')
        assert sale.get_status_display() == 'Reserva'

    def test_collection_summary_balance_pending_excludes_paid(
        self, setup_basic, make_vehicle, credito,
    ):
        sale = _make_sale(setup_basic, make_vehicle(), credito, 'B/26')
        _make_q(sale, 1, date.today() - timedelta(days=10), status='paid', amount=2_000_000)
        _make_q(sale, 2, date.today() + timedelta(days=30), amount=2_000_000)
        _make_q(sale, 3, date.today() + timedelta(days=60), amount=2_000_000)
        s = sale.collection_summary
        # Solo las 2 pending suman al balance
        assert s['balance_pending'] == 4_000_000
        assert s['n_paid'] == 1
        assert s['n_total'] == 3
