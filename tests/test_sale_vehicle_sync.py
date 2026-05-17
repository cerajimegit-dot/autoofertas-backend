"""Tests para la sincronización automática de Sale → Vehicle.state
y para el cálculo dinámico de Quotum.is_overdue / effective_status.

Cubre los bugs que dispararon estos cambios:
  - 25+ vehículos quedaban en 'available' aunque tenían una Sale activa.
  - La página /quotas con filtro "Vencidas" mostraba 62 cuando había ~970
    cuotas pending vencidas + 62 legacy con status='overdue' literal.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from core.models import (
    Brand, VehicleModel, Vehicle, Customer, PaymentForm, Sale, Quotum,
)

pytestmark = pytest.mark.django_db


# ---------- Fixtures locales ----------

@pytest.fixture
def brand(test_enterprise):
    return Brand.objects.create(enterprise=test_enterprise, name='Toyota')


@pytest.fixture
def model(test_enterprise, brand):
    return VehicleModel.objects.create(
        enterprise=test_enterprise, brand=brand, name='Vitz 1.0',
    )


@pytest.fixture
def make_vehicle(test_enterprise, test_branch, brand, model):
    """Factory: crea vehículos con VIN único."""
    counter = {'n': 0}
    def _factory(state='available', vin=None, price=10_000_000):
        counter['n'] += 1
        return Vehicle.objects.create(
            enterprise=test_enterprise,
            branch=test_branch,
            brand=brand,
            model=model,
            year=2018,
            vin=vin or f'VINTEST{counter["n"]:05d}',
            price=Decimal(str(price)),
            fob=Decimal('0'),
            container=Decimal('0'),
            dispatch=Decimal('0'),
            cam_vol=Decimal('0'),
            state=state,
        )
    return _factory


@pytest.fixture
def customer(test_enterprise):
    return Customer.objects.create(
        enterprise=test_enterprise,
        first_name='Mario',
        last_name='Bogado',
        document_number='1234567',
        phone='0981 123 456',
    )


@pytest.fixture
def make_sale(test_enterprise, test_branch, customer):
    """Factory: crea ventas con sale_number único."""
    counter = {'n': 0}
    def _factory(vehicle=None, status='completed', price=10_000_000):
        counter['n'] += 1
        return Sale.objects.create(
            enterprise=test_enterprise,
            branch=test_branch,
            sale_number=f'TEST{counter["n"]:03d}/26',
            customer=customer,
            vehicle=vehicle,
            unit_price=Decimal(str(price)),
            total_price=Decimal(str(price)),
            status=status,
        )
    return _factory


# ---------- Sale → Vehicle.state ----------

class TestSaleSyncsVehicleState:

    def test_completed_sale_marks_vehicle_sold(self, make_vehicle, make_sale):
        v = make_vehicle(state='available')
        make_sale(vehicle=v, status='completed')
        v.refresh_from_db()
        assert v.state == 'sold'

    def test_pending_sale_marks_vehicle_reserved(self, make_vehicle, make_sale):
        v = make_vehicle(state='available')
        make_sale(vehicle=v, status='pending')
        v.refresh_from_db()
        assert v.state == 'reserved'

    def test_cancelled_sale_releases_vehicle(self, make_vehicle, make_sale):
        v = make_vehicle(state='available')
        s = make_sale(vehicle=v, status='completed')
        v.refresh_from_db()
        assert v.state == 'sold'

        s.status = 'cancelled'
        s.save()
        v.refresh_from_db()
        assert v.state == 'available'

    def test_pending_to_completed_keeps_or_promotes(self, make_vehicle, make_sale):
        v = make_vehicle(state='available')
        s = make_sale(vehicle=v, status='pending')
        v.refresh_from_db()
        assert v.state == 'reserved'

        s.status = 'completed'
        s.save()
        v.refresh_from_db()
        assert v.state == 'sold'

    def test_swap_vehicle_releases_old_and_marks_new(self, make_vehicle, make_sale):
        v1 = make_vehicle(state='available')
        v2 = make_vehicle(state='available')
        s = make_sale(vehicle=v1, status='completed')
        v1.refresh_from_db(); v2.refresh_from_db()
        assert v1.state == 'sold'
        assert v2.state == 'available'

        s.vehicle = v2
        s.save()
        v1.refresh_from_db(); v2.refresh_from_db()
        assert v1.state == 'available', 'el vehículo desasignado debe liberarse'
        assert v2.state == 'sold',      'el nuevo debe quedar vendido'

    def test_does_not_release_if_other_active_sale_exists(
        self, make_vehicle, make_sale,
    ):
        v = make_vehicle(state='available')
        s1 = make_sale(vehicle=v, status='completed')
        s2 = make_sale(vehicle=v, status='pending')
        # s2 reservó el mismo vehículo (uso inusual pero legal en el modelo).
        v.refresh_from_db()
        # La última save fue s2 que pidió 'reserved' — pero como hay s1
        # completed activa, esperamos que el state actual sea consistente con
        # alguna venta activa. Lo importante es que cancelar s1 no libere
        # el vehículo porque s2 sigue activa.
        assert v.state in ('sold', 'reserved')

        s1.status = 'cancelled'
        s1.save()
        v.refresh_from_db()
        assert v.state != 'available', (
            'no se debe liberar mientras s2 sigue activa'
        )

    def test_delete_sale_releases_vehicle(self, make_vehicle, make_sale):
        v = make_vehicle(state='available')
        s = make_sale(vehicle=v, status='completed')
        v.refresh_from_db(); assert v.state == 'sold'

        s.delete()
        v.refresh_from_db()
        assert v.state == 'available'

    def test_sale_without_vehicle_does_not_explode(self, make_sale):
        # Las 17 ventas reales sin vehículo no deben romper el save.
        s = make_sale(vehicle=None, status='completed')
        assert s.pk is not None
        assert s.vehicle_id is None


# ---------- Quotum.is_overdue dinámico ----------

class TestQuotumIsOverdue:

    @pytest.fixture
    def sale_with_vehicle(self, make_vehicle, make_sale):
        v = make_vehicle(state='available')
        return make_sale(vehicle=v, status='completed')

    def _make_quota(self, enterprise, sale, **kwargs):
        defaults = dict(
            enterprise=enterprise, sale=sale,
            customer=sale.customer, quota_number=1,
            total_plan=1, amount=Decimal('1000000'),
            due_date=date.today(), status='pending',
        )
        defaults.update(kwargs)
        return Quotum.objects.create(**defaults)

    def test_pending_past_due_is_overdue(
        self, sale_with_vehicle, test_enterprise,
    ):
        q = self._make_quota(
            test_enterprise, sale_with_vehicle,
            due_date=date.today() - timedelta(days=5),
            status='pending',
        )
        assert q.is_overdue is True
        assert q.effective_status == 'overdue'

    def test_pending_future_due_is_not_overdue(
        self, sale_with_vehicle, test_enterprise,
    ):
        q = self._make_quota(
            test_enterprise, sale_with_vehicle,
            due_date=date.today() + timedelta(days=5),
            status='pending',
        )
        assert q.is_overdue is False
        assert q.effective_status == 'pending'

    def test_paid_quota_never_overdue(
        self, sale_with_vehicle, test_enterprise,
    ):
        q = self._make_quota(
            test_enterprise, sale_with_vehicle,
            due_date=date.today() - timedelta(days=100),
            status='paid',
        )
        assert q.is_overdue is False
        assert q.effective_status == 'paid'

    def test_cancelled_quota_never_overdue(
        self, sale_with_vehicle, test_enterprise,
    ):
        q = self._make_quota(
            test_enterprise, sale_with_vehicle,
            due_date=date.today() - timedelta(days=100),
            status='cancelled',
        )
        assert q.is_overdue is False
        assert q.effective_status == 'cancelled'

    def test_legacy_status_overdue_is_overdue(
        self, sale_with_vehicle, test_enterprise,
    ):
        # Las 62 cuotas legacy con status='overdue' literal en BD.
        q = self._make_quota(
            test_enterprise, sale_with_vehicle,
            due_date=date.today() - timedelta(days=30),
            status='overdue',
        )
        assert q.is_overdue is True
        assert q.effective_status == 'overdue'

    def test_due_today_is_not_overdue(
        self, sale_with_vehicle, test_enterprise,
    ):
        # Convención: vencida = due_date < hoy. Vence hoy todavía no.
        q = self._make_quota(
            test_enterprise, sale_with_vehicle,
            due_date=date.today(),
            status='pending',
        )
        assert q.is_overdue is False
