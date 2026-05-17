"""Tests del modelo CashMovement, su auto-creación desde Sale/Quotum y los endpoints."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from rest_framework.test import APIClient

from core.models import (
    Brand, VehicleModel, Vehicle, Customer, PaymentForm,
    Sale, Quotum, CashMovement,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api(test_admin_user):
    c = APIClient()
    c.force_authenticate(user=test_admin_user)
    return c


@pytest.fixture
def brand(test_enterprise):
    return Brand.objects.create(enterprise=test_enterprise, name='Toyota')


@pytest.fixture
def model(test_enterprise, brand):
    return VehicleModel.objects.create(
        enterprise=test_enterprise, brand=brand, name='Vitz 1.0',
    )


@pytest.fixture
def vehicle(test_enterprise, test_branch, brand, model):
    return Vehicle.objects.create(
        enterprise=test_enterprise, branch=test_branch,
        brand=brand, model=model, year=2018,
        vin='TESTCASHVIN', price=Decimal('10000000'),
        fob=Decimal('0'), container=Decimal('0'),
        dispatch=Decimal('0'), cam_vol=Decimal('0'),
        state='available',
    )


@pytest.fixture
def vehicle2(test_enterprise, test_branch, brand, model):
    return Vehicle.objects.create(
        enterprise=test_enterprise, branch=test_branch,
        brand=brand, model=model, year=2018,
        vin='TESTCASHVIN2', price=Decimal('15000000'),
        fob=Decimal('0'), container=Decimal('0'),
        dispatch=Decimal('0'), cam_vol=Decimal('0'),
        state='available',
    )


@pytest.fixture
def customer(test_enterprise):
    return Customer.objects.create(
        enterprise=test_enterprise, first_name='Mario',
        last_name='Bogado', document_number='4444444',
        phone='0981111',
    )


@pytest.fixture
def contado_pf(test_enterprise):
    return PaymentForm.objects.create(enterprise=test_enterprise, name='CONTADO')


@pytest.fixture
def credito_pf(test_enterprise):
    return PaymentForm.objects.create(enterprise=test_enterprise, name='CREDITO')


class TestAutoCreateFromSale:
    """Cuando se crea/edita una Sale, se generan los movimientos automáticos."""

    def test_sale_contado_completed_creates_in_movement(
        self, test_enterprise, test_branch, customer, vehicle, contado_pf,
    ):
        sale = Sale.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            sale_number='C/26', customer=customer, vehicle=vehicle,
            unit_price=Decimal('10000000'), total_price=Decimal('10000000'),
            payment_form=contado_pf, status='completed',
        )
        mov = CashMovement.objects.filter(sale=sale, kind='venta_contado').first()
        assert mov is not None
        assert mov.direction == 'in'
        assert mov.amount == Decimal('10000000')
        assert mov.is_auto is True
        assert 'C/26' in mov.description

    def test_sale_credito_with_down_payment_creates_seña(
        self, test_enterprise, test_branch, customer, vehicle, credito_pf,
    ):
        sale = Sale.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            sale_number='Cr/26', customer=customer, vehicle=vehicle,
            unit_price=Decimal('10000000'), total_price=Decimal('10000000'),
            down_payment=Decimal('3000000'),
            payment_form=credito_pf, status='completed',
        )
        sena = CashMovement.objects.filter(sale=sale, kind='seña_credito').first()
        assert sena is not None
        assert sena.amount == Decimal('3000000')
        assert sena.direction == 'in'
        # No debe crear movimiento de venta_contado (es CREDITO)
        assert not CashMovement.objects.filter(sale=sale, kind='venta_contado').exists()

    def test_pending_sale_does_not_create_movement(
        self, test_enterprise, test_branch, customer, vehicle, contado_pf,
    ):
        sale = Sale.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            sale_number='P/26', customer=customer, vehicle=vehicle,
            unit_price=Decimal('10000000'), total_price=Decimal('10000000'),
            payment_form=contado_pf, status='pending',
        )
        assert not CashMovement.objects.filter(sale=sale).exists()

    def test_cancelling_sale_removes_auto_movements(
        self, test_enterprise, test_branch, customer, vehicle, contado_pf,
    ):
        sale = Sale.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            sale_number='X/26', customer=customer, vehicle=vehicle,
            unit_price=Decimal('10000000'), total_price=Decimal('10000000'),
            payment_form=contado_pf, status='completed',
        )
        assert CashMovement.objects.filter(sale=sale).exists()

        sale.status = 'cancelled'
        sale.save()
        assert not CashMovement.objects.filter(sale=sale, is_auto=True).exists()


class TestAutoCreateFromQuota:

    @pytest.fixture
    def sale(self, test_enterprise, test_branch, customer, vehicle2, credito_pf):
        return Sale.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            sale_number='Q/26', customer=customer, vehicle=vehicle2,
            unit_price=Decimal('15000000'), total_price=Decimal('15000000'),
            payment_form=credito_pf, status='completed',
        )

    def test_paid_quota_creates_cobro_cuota(self, test_enterprise, sale):
        q = Quotum.objects.create(
            enterprise=test_enterprise, sale=sale, customer=sale.customer,
            quota_number=1, total_plan=12,
            amount=Decimal('1000000'),
            due_date=date.today(),
            status='paid',
            payment_date=date(2026, 2, 15),
        )
        mov = CashMovement.objects.filter(quota=q, kind='cobro_cuota').first()
        assert mov is not None
        assert mov.amount == Decimal('1000000')
        assert mov.direction == 'in'
        assert mov.date == date(2026, 2, 15)
        assert mov.is_auto is True

    def test_marking_unpaid_removes_movement(self, test_enterprise, sale):
        q = Quotum.objects.create(
            enterprise=test_enterprise, sale=sale, customer=sale.customer,
            quota_number=1, total_plan=12,
            amount=Decimal('1000000'), due_date=date.today(),
            status='paid', payment_date=date.today(),
        )
        assert CashMovement.objects.filter(quota=q).exists()

        q.status = 'pending'
        q.payment_date = None
        q.save()
        assert not CashMovement.objects.filter(quota=q, is_auto=True).exists()

    def test_pending_quota_no_movement(self, test_enterprise, sale):
        Quotum.objects.create(
            enterprise=test_enterprise, sale=sale, customer=sale.customer,
            quota_number=1, total_plan=12,
            amount=Decimal('1000000'), due_date=date.today(),
            status='pending',
        )
        assert not CashMovement.objects.exists()


class TestManualMovements:
    """Movimientos cargados manualmente desde la API (gastos, compras, etc.)."""

    def test_create_manual_expense(self, api, test_branch):
        r = api.post('/api/cash-movements/', data={
            'branch': test_branch.id,
            'date': '2026-02-19',
            'kind': 'alquiler',
            'direction': 'out',
            'amount': '8400000',
            'description': 'PAGO DE ALQUILER FEBRERO/26',
            'currency': 'PYG',
        }, format='json')
        assert r.status_code == 201, r.data
        assert r.data['is_auto'] is False
        assert r.data['direction'] == 'out'
        assert r.data['signed_amount'] == -8400000

    def test_create_compra_exterior_with_usd(self, api, test_branch):
        r = api.post('/api/cash-movements/', data={
            'branch': test_branch.id,
            'date': '2026-02-06',
            'kind': 'compra_exterior',
            'direction': 'out',
            'amount': '102438600',
            'currency': 'USD',
            'amount_usd': '15521',
            'exchange_rate': '6600',
            'provider': 'AUTOCOM',
            'description': 'AUTOCOM CANCELACION 5 UNID. Y SEÑA 8 UNID.',
        }, format='json')
        assert r.status_code == 201
        assert r.data['amount_usd'] == '15521.00'
        assert r.data['provider'] == 'AUTOCOM'

    def test_reject_negative_amount(self, api):
        r = api.post('/api/cash-movements/', data={
            'date': '2026-02-19',
            'kind': 'alquiler',
            'direction': 'out',
            'amount': '-1000',
            'description': 'mal',
        }, format='json')
        assert r.status_code == 400
        assert 'amount' in r.data

    def test_cannot_delete_auto_movement(
        self, api, test_enterprise, test_branch, customer, vehicle, contado_pf,
    ):
        sale = Sale.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            sale_number='D/26', customer=customer, vehicle=vehicle,
            unit_price=Decimal('10000000'), total_price=Decimal('10000000'),
            payment_form=contado_pf, status='completed',
        )
        mov = CashMovement.objects.get(sale=sale, kind='venta_contado')
        r = api.delete(f'/api/cash-movements/{mov.id}/')
        assert r.status_code == 400


class TestSummary:

    def test_summary_aggregates_in_out_and_by_kind(
        self, api, test_enterprise, test_branch,
    ):
        CashMovement.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            date=date(2026, 2, 10), kind='gasto_playa',
            direction='out', amount=Decimal('10000000'),
            description='GASTOS PLAYA',
        )
        CashMovement.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            date=date(2026, 2, 12), kind='cobro_cuota',
            direction='in', amount=Decimal('1500000'),
            description='cobro test',
        )
        CashMovement.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            date=date(2026, 2, 15), kind='alquiler',
            direction='out', amount=Decimal('8000000'),
            description='alquiler',
        )

        r = api.get('/api/cash-movements/summary/'
                    '?date_from=2026-02-01&date_to=2026-02-28')
        assert r.status_code == 200
        assert r.data['ingresos']['total'] == 1_500_000
        assert r.data['egresos']['total'] == 18_000_000
        assert r.data['neto'] == 1_500_000 - 18_000_000
        kinds = [(b['kind'], b['total']) for b in r.data['by_kind']]
        assert ('gasto_playa', 10_000_000.0) in kinds
        assert ('alquiler', 8_000_000.0) in kinds
        assert ('cobro_cuota', 1_500_000.0) in kinds

    def test_summary_filters_by_branch(
        self, api, test_enterprise, test_branch,
    ):
        from core.models import Branch
        other_branch = Branch.objects.create(
            enterprise=test_enterprise, name='Otra', code='OT',
        )
        CashMovement.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            date=date.today(), kind='gasto_playa',
            direction='out', amount=Decimal('1000000'), description='A',
        )
        CashMovement.objects.create(
            enterprise=test_enterprise, branch=other_branch,
            date=date.today(), kind='gasto_playa',
            direction='out', amount=Decimal('5000000'), description='B',
        )
        r = api.get(f'/api/cash-movements/summary/?branch={test_branch.id}')
        assert r.data['egresos']['total'] == 1_000_000
