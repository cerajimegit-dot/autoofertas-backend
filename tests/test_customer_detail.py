"""Tests del flujo /customers/:id — filtros y aislamiento entre clientes."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from rest_framework.test import APIClient

from core.models import (
    Brand, VehicleModel, Vehicle, Customer, Sale, Quotum,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api(test_admin_user):
    c = APIClient()
    c.force_authenticate(user=test_admin_user)
    return c


@pytest.fixture
def cliente_a(test_enterprise):
    return Customer.objects.create(
        enterprise=test_enterprise, first_name='Ana', last_name='Pérez',
        document_number='1111111', phone='0981 111 111',
    )


@pytest.fixture
def cliente_b(test_enterprise):
    return Customer.objects.create(
        enterprise=test_enterprise, first_name='Bruno', last_name='Acosta',
        document_number='2222222',
    )


@pytest.fixture
def make_vehicle(test_enterprise, test_branch):
    brand = Brand.objects.create(enterprise=test_enterprise, name='Toyota')
    model = VehicleModel.objects.create(
        enterprise=test_enterprise, brand=brand, name='Vitz',
    )
    n = {'i': 0}
    def _f():
        n['i'] += 1
        return Vehicle.objects.create(
            enterprise=test_enterprise, branch=test_branch,
            brand=brand, model=model, year=2018,
            vin=f'V{n["i"]:05d}',
            price=Decimal('20000000'), fob=Decimal('0'),
            container=Decimal('0'), dispatch=Decimal('0'), cam_vol=Decimal('0'),
            state='available',
        )
    return _f


def _make_sale(enterprise, branch, customer, vehicle, sale_number, price=20_000_000):
    return Sale.objects.create(
        enterprise=enterprise, branch=branch,
        sale_number=sale_number, customer=customer, vehicle=vehicle,
        unit_price=Decimal(str(price)), total_price=Decimal(str(price)),
        status='completed',
    )


def _make_quota(enterprise, sale, n, due_date, amount=1_000_000, status='pending'):
    return Quotum.objects.create(
        enterprise=enterprise, sale=sale, customer=sale.customer,
        quota_number=n, total_plan=12,
        amount=Decimal(str(amount)), due_date=due_date, status=status,
    )


class TestCustomerFilterIsolation:
    """Las queries con ?customer= sólo deben devolver datos de ESE cliente."""

    def test_sales_filter_by_customer(
        self, api, test_enterprise, test_branch, cliente_a, cliente_b, make_vehicle,
    ):
        va, vb = make_vehicle(), make_vehicle()
        _make_sale(test_enterprise, test_branch, cliente_a, va, 'CMA/26')
        _make_sale(test_enterprise, test_branch, cliente_b, vb, 'CMB/26')

        r = api.get(f'/api/sales/?customer={cliente_a.id}')
        assert r.status_code == 200
        items = r.data.get('results', r.data)
        nums = [s['sale_number'] for s in items]
        assert 'CMA/26' in nums
        assert 'CMB/26' not in nums, 'no debe traer ventas de otro cliente'

    def test_quotas_filter_by_customer(
        self, api, test_enterprise, test_branch, cliente_a, cliente_b, make_vehicle,
    ):
        va, vb = make_vehicle(), make_vehicle()
        sa = _make_sale(test_enterprise, test_branch, cliente_a, va, 'QA/26')
        sb = _make_sale(test_enterprise, test_branch, cliente_b, vb, 'QB/26')
        _make_quota(test_enterprise, sa, 1, date.today() + timedelta(days=30))
        _make_quota(test_enterprise, sb, 1, date.today() + timedelta(days=30))

        r = api.get(f'/api/quotas/?customer={cliente_a.id}')
        assert r.status_code == 200
        items = r.data.get('results', r.data)
        assert len(items) == 1
        assert items[0]['customer_name'] == cliente_a.full_name


class TestCustomerFullEndpoint:
    """El endpoint /customers/{id}/full/ devuelve todo en 1 round-trip."""

    def test_full_returns_customer_sales_quotas_summary(
        self, api, test_enterprise, test_branch, cliente_a, make_vehicle,
    ):
        from datetime import date, timedelta
        from decimal import Decimal
        v = make_vehicle()
        sale = _make_sale(test_enterprise, test_branch, cliente_a, v, 'CMA/26',
                          price=10_000_000)
        # 3 cuotas: una pagada, una pendiente, una vencida
        _make_quota(test_enterprise, sale, 1,
                    date.today() - timedelta(days=60),
                    amount=2_000_000, status='paid')
        _make_quota(test_enterprise, sale, 2,
                    date.today() + timedelta(days=30),
                    amount=2_000_000, status='pending')
        _make_quota(test_enterprise, sale, 3,
                    date.today() - timedelta(days=5),
                    amount=2_000_000, status='pending')

        r = api.get(f'/api/customers/{cliente_a.id}/full/')
        assert r.status_code == 200

        # estructura
        assert 'customer' in r.data
        assert 'sales' in r.data
        assert 'quotas' in r.data
        assert 'summary' in r.data

        # datos
        assert r.data['customer']['first_name'] == cliente_a.first_name
        assert len(r.data['sales']) == 1
        assert r.data['sales'][0]['sale_number'] == 'CMA/26'
        assert len(r.data['quotas']) == 3

        s = r.data['summary']
        assert s['tot_comprado'] == 10_000_000
        assert s['n_ventas'] == 1
        assert s['tot_cobrado'] == 2_000_000
        assert s['n_pagadas'] == 1
        # Vencidas: la cuota con due_date pasado y status pending
        assert s['n_vencidas'] == 1
        assert s['tot_vencido'] == 2_000_000
        # Pendientes (al día): la cuota con due_date futura
        assert s['n_pendientes'] == 1


class TestCustomerRetrieve:

    def test_retrieve_returns_basic_fields(self, api, cliente_a):
        r = api.get(f'/api/customers/{cliente_a.id}/')
        assert r.status_code == 200
        assert r.data['first_name'] == 'Ana'
        assert r.data['document_number'] == '1111111'
        assert 'sales_count' in r.data

    def test_retrieve_404_for_other_enterprise(
        self, api, test_admin_user,
    ):
        from core.models import Enterprise
        other = Enterprise.objects.create(name='Otro', ruc='999', email='x@y.com')
        otro_cli = Customer.objects.create(
            enterprise=other, first_name='Z', last_name='Z',
            document_number='9999999',
        )
        r = api.get(f'/api/customers/{otro_cli.id}/')
        # Multi-tenant: ni siquiera lo encuentra
        assert r.status_code == 404
