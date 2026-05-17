"""Tests para Quotum.payment_method + mark_as_paid + backfill desde notes."""

import pytest
import re
from datetime import date
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
def quota_pending(test_enterprise, test_branch):
    brand = Brand.objects.create(enterprise=test_enterprise, name='Toyota')
    model = VehicleModel.objects.create(
        enterprise=test_enterprise, brand=brand, name='Vitz',
    )
    customer = Customer.objects.create(
        enterprise=test_enterprise, first_name='Z', last_name='Z',
        document_number='8888888', phone='0981000000',
    )
    vehicle = Vehicle.objects.create(
        enterprise=test_enterprise, branch=test_branch,
        brand=brand, model=model, year=2018,
        vin='TESTVIN001', price=Decimal('10000000'),
        fob=Decimal('0'), container=Decimal('0'),
        dispatch=Decimal('0'), cam_vol=Decimal('0'),
    )
    sale = Sale.objects.create(
        enterprise=test_enterprise, branch=test_branch,
        sale_number='CMTEST/26', customer=customer, vehicle=vehicle,
        unit_price=Decimal('10000000'), total_price=Decimal('10000000'),
        status='completed',
    )
    return Quotum.objects.create(
        enterprise=test_enterprise, sale=sale, customer=customer,
        quota_number=1, total_plan=12,
        amount=Decimal('1000000'), due_date=date.today(),
        status='pending',
    )


class TestMarkAsPaidWithMethod:

    def test_mark_as_paid_with_payment_method(self, api, quota_pending):
        r = api.post(f'/api/quotas/{quota_pending.id}/mark_as_paid/', data={
            'payment_date': '2026-05-10',
            'payment_method': 'TB',
            'notes': 'banco continental',
        }, format='json')
        assert r.status_code == 200
        quota_pending.refresh_from_db()
        assert quota_pending.status == 'paid'
        assert quota_pending.payment_method == 'TB'
        assert quota_pending.payment_date.isoformat() == '2026-05-10'
        # La nota libre NO debe llevar el prefijo [TB] — eso vivía en el workaround.
        assert quota_pending.notes == 'banco continental'

    def test_mark_as_paid_rejects_invalid_method(self, api, quota_pending):
        r = api.post(f'/api/quotas/{quota_pending.id}/mark_as_paid/', data={
            'payment_method': 'XYZ',
        }, format='json')
        assert r.status_code == 400
        assert 'payment_method' in r.data

    def test_mark_as_paid_without_method_works(self, api, quota_pending):
        # Backwards-compat: si el frontend viejo no manda payment_method, no rompe.
        r = api.post(f'/api/quotas/{quota_pending.id}/mark_as_paid/', data={},
                     format='json')
        assert r.status_code == 200
        quota_pending.refresh_from_db()
        assert quota_pending.status == 'paid'
        assert quota_pending.payment_method in (None, '')


class TestBackfillRegex:
    """El backfill de la migración 0008 parsea [XX] al inicio de notes.

    Lo testeamos contra el regex directamente — no podemos ejecutar la
    migración real en cada test, pero validamos que la lógica de matching
    cubre los casos típicos vistos en BD.
    """

    PATTERN = re.compile(r'^\s*\[(EF|TB|CJ|AC)\]\s*', re.IGNORECASE)

    @pytest.mark.parametrize('note,expected_method,expected_rest', [
        ('[EF]',                       'EF', ''),
        ('[EF] ',                      'EF', ''),
        ('[EF] efectivo en mano',      'EF', 'efectivo en mano'),
        ('[TB] N° 1234567',            'TB', 'N° 1234567'),
        ('[cj] minuscula',             'cj', 'minuscula'),
        ('  [AC]   espacio inicial',   'AC', 'espacio inicial'),
        ('sin prefijo',                None, 'sin prefijo'),
        ('[XX] forma rara',            None, '[XX] forma rara'),
        ('',                           None, ''),
    ])
    def test_pattern_extracts_method(self, note, expected_method, expected_rest):
        m = self.PATTERN.match(note)
        if expected_method is None:
            assert m is None
        else:
            assert m is not None
            assert m.group(1).upper() == expected_method.upper()
            rest = self.PATTERN.sub('', note, count=1).strip()
            assert rest == expected_rest


class TestPaymentMethodInSerializer:

    def test_payment_method_visible_in_list(self, api, quota_pending):
        quota_pending.payment_method = 'EF'
        quota_pending.status = 'paid'
        quota_pending.save()
        r = api.get(f'/api/quotas/?customer={quota_pending.customer_id}')
        assert r.status_code == 200
        items = r.data.get('results', r.data)
        assert items[0]['payment_method'] == 'EF'
        assert items[0]['payment_method_display'] == 'Efectivo'
