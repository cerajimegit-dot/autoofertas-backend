"""Tests del endpoint /api/dashboard/health/.

Verificamos que las 6 métricas se calculen correctamente con datos
deterministas:

  1. Tasa de morosidad
  2. Ticket promedio
  3. Días promedio de pago
  4. Vehículos estancados >90d
  5. Top vendedor
  6. Tasa de conversión

Cubrimos también:
  - Tenancy: ventas/cuotas de otra empresa no se cuentan.
  - Período: usar date_from/date_to filtra correctamente.
"""

from decimal import Decimal
from datetime import date, datetime, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    CustomUser, Enterprise, Branch, Customer, Brand, VehicleModel,
    Vehicle, Sale, Quotum, PaymentForm,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    e1 = Enterprise.objects.create(
        name='E1', ruc='11111111', email='e1@x.com',
        phone='1', address='x', city='Asunción',
    )
    e2 = Enterprise.objects.create(
        name='E2', ruc='22222222', email='e2@x.com',
        phone='2', address='y', city='Asunción',
    )

    b1 = Branch.objects.create(enterprise=e1, name='A', code='A')
    b2 = Branch.objects.create(enterprise=e2, name='B', code='A')

    brand = Brand.objects.create(enterprise=e1, name='Toyota')
    model = VehicleModel.objects.create(enterprise=e1, brand=brand, name='Vitz')
    pf = PaymentForm.objects.create(enterprise=e1, name='Contado')

    # 2 vendedores
    seller1 = CustomUser.objects.create_user(
        username='v1', email='v1@e1.com', password='x',
        enterprise=e1, role='vendor', first_name='Mati',
    )
    seller2 = CustomUser.objects.create_user(
        username='v2', email='v2@e1.com', password='x',
        enterprise=e1, role='vendor', first_name='Marce',
    )

    # 2 clientes para ver "conversión"
    c1 = Customer.objects.create(
        enterprise=e1, first_name='A', last_name='B',
        document_type='ci', document_number='111', email='a@x.com',
        phone='1', city='X',
    )
    c2 = Customer.objects.create(
        enterprise=e1, first_name='C', last_name='D',
        document_type='ci', document_number='222', email='c@x.com',
        phone='2', city='X',
    )

    def make_vehicle(year, vin, created_offset_days=0):
        """created_offset_days: <0 = antes; útil para estancados."""
        v = Vehicle.objects.create(
            enterprise=e1, branch=b1, brand=brand, model=model, year=year,
            vin=vin, state='available',
            fob=Decimal('0'), container=Decimal('0'), dispatch=Decimal('0'),
            cam_vol=Decimal('0'), price=Decimal('1'),
        )
        if created_offset_days:
            # Forzamos created_at hacia atrás para simular vehículo viejo
            past = timezone.now() + timedelta(days=created_offset_days)
            Vehicle.objects.filter(pk=v.pk).update(created_at=past)
        return v

    # Vehículos:
    #   - v_estancado: 100 días, AVAILABLE, nunca se vende → cuenta para
    #     "estancados". Lo dejamos fuera de las Sales para que Sale.save()
    #     no lo auto-marque como sold.
    #   - v_viejo, v_nuevo, v_vendido: los usamos en las 3 ventas; sus
    #     estados terminan en 'sold' por el auto-sync de Sale.save.
    v_estancado = make_vehicle(2017, 'VINESTANCADO', created_offset_days=-100)
    v_viejo = make_vehicle(2018, 'VINVIEJO', created_offset_days=-100)
    v_nuevo = make_vehicle(2024, 'VINNUEVO')
    v_vendido = make_vehicle(2020, 'VINVENDIDO')

    # Ventas en el período mayo 2026 — 3 ventas, una de seller1 (alto), dos de seller2 (bajos)
    s1 = Sale.objects.create(
        enterprise=e1, branch=b1, customer=c1, vehicle=v_viejo,
        sale_number='V1', sale_date=datetime(2026, 5, 5),
        unit_price=Decimal('100000000'), total_price=Decimal('100000000'),
        payment_form=pf, seller=seller1, status='completed',
    )
    Sale.objects.create(
        enterprise=e1, branch=b1, customer=c1, vehicle=v_nuevo,
        sale_number='V2', sale_date=datetime(2026, 5, 10),
        unit_price=Decimal('50000000'), total_price=Decimal('50000000'),
        payment_form=pf, seller=seller2, status='completed',
    )
    Sale.objects.create(
        enterprise=e1, branch=b1, customer=c2, vehicle=v_vendido,
        sale_number='V3', sale_date=datetime(2026, 5, 15),
        unit_price=Decimal('40000000'), total_price=Decimal('40000000'),
        payment_form=pf, seller=seller2, status='completed',
    )
    # 1 venta en otra empresa — no debe contar
    Sale.objects.create(
        enterprise=e2, branch=b2, customer=c1, vehicle=v_viejo,
        sale_number='V-OTRA', sale_date=datetime(2026, 5, 1),
        unit_price=Decimal('9999999999'), total_price=Decimal('9999999999'),
        payment_form=pf, status='completed',
    )

    # Cuotas: 4 sobre la venta s1 — 2 pagadas (1 a tiempo, 1 tarde 5d),
    # 1 vencida sin pagar, 1 todavía pendiente.
    Quotum.objects.create(
        enterprise=e1, sale=s1, customer=c1, total_plan=4,
        quota_number=1, amount=Decimal('25000000'),
        due_date=date(2026, 4, 1), payment_date=date(2026, 4, 1),
        status='paid',
    )
    Quotum.objects.create(
        enterprise=e1, sale=s1, customer=c1, total_plan=4,
        quota_number=2, amount=Decimal('25000000'),
        due_date=date(2026, 4, 15), payment_date=date(2026, 4, 20),  # 5 días tarde
        status='paid',
    )
    # Cuota vencida sin pagar (la consideramos morosa)
    Quotum.objects.create(
        enterprise=e1, sale=s1, customer=c1, total_plan=4,
        quota_number=3, amount=Decimal('25000000'),
        due_date=date(2026, 5, 1), status='pending',
    )
    Quotum.objects.create(
        enterprise=e1, sale=s1, customer=c1, total_plan=4,
        quota_number=4, amount=Decimal('25000000'),
        due_date=date(2027, 5, 1), status='pending',
    )

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {
        'client': client,
        'e1': e1, 'e2': e2,
        'seller1_id': seller1.id, 'seller2_id': seller2.id,
    }


def test_health_devuelve_estructura_completa(setup):
    r = setup['client'].get('/api/dashboard/health/?date_from=2026-05-01&date_to=2026-05-31')
    assert r.status_code == 200
    body = r.json()
    for key in ['tasa_morosidad', 'ticket_promedio', 'dias_promedio_pago',
                'vehiculos_estancados_90d', 'top_vendedor',
                'tasa_conversion_clientes', 'periodo']:
        assert key in body, f'falta {key}'


def test_tasa_morosidad(setup):
    """1 vencida sin pagar / 4 activas = 25%."""
    r = setup['client'].get('/api/dashboard/health/?date_from=2026-05-01&date_to=2026-05-31')
    body = r.json()
    assert body['tasa_morosidad']['n_vencidas'] == 1
    assert body['tasa_morosidad']['n_activas'] == 4
    assert body['tasa_morosidad']['porcentaje'] == 25.0


def test_ticket_promedio(setup):
    """3 ventas: 100M, 50M, 40M → promedio 63.333M."""
    r = setup['client'].get('/api/dashboard/health/?date_from=2026-05-01&date_to=2026-05-31')
    body = r.json()
    assert body['ticket_promedio']['n_ventas'] == 3
    # Promedio (100 + 50 + 40) / 3 = 63.333...
    assert 63_333_000 <= body['ticket_promedio']['monto'] <= 63_334_000


def test_dias_promedio_pago(setup):
    """2 cuotas pagadas en el período:
       - una el mismo día (0 días)
       - otra 5 días tarde (+5)
       Promedio = 2.5"""
    # Período abril/mayo 2026 cubre los payment_dates
    r = setup['client'].get('/api/dashboard/health/?date_from=2026-04-01&date_to=2026-05-31')
    body = r.json()
    assert body['dias_promedio_pago']['n_muestras'] == 2
    assert body['dias_promedio_pago']['dias'] == 2.5


def test_vehiculos_estancados(setup):
    """1 vehículo con created_at -100d que está available."""
    r = setup['client'].get('/api/dashboard/health/?date_from=2026-05-01&date_to=2026-05-31')
    body = r.json()
    assert body['vehiculos_estancados_90d']['count'] == 1


def test_top_vendedor_por_monto(setup):
    """seller1 vendió 100M; seller2 vendió 50+40=90M. Gana seller1."""
    r = setup['client'].get('/api/dashboard/health/?date_from=2026-05-01&date_to=2026-05-31')
    body = r.json()
    assert body['top_vendedor'] is not None
    assert body['top_vendedor']['id'] == setup['seller1_id']
    assert body['top_vendedor']['total'] == 100_000_000


def test_tasa_conversion(setup):
    """3 ventas / 2 clientes únicos = 1.5"""
    r = setup['client'].get('/api/dashboard/health/?date_from=2026-05-01&date_to=2026-05-31')
    body = r.json()
    assert body['tasa_conversion_clientes']['ventas'] == 3
    assert body['tasa_conversion_clientes']['clientes_unicos'] == 2
    assert body['tasa_conversion_clientes']['ratio'] == 1.5


def test_tenancy_no_filtra_otra_empresa(setup):
    """La venta de 99.9B de e2 no debe inflar el ticket promedio."""
    r = setup['client'].get('/api/dashboard/health/?date_from=2026-05-01&date_to=2026-05-31')
    body = r.json()
    # Si la otra empresa hubiera entrado, el ticket promedio sería ~25.000M.
    assert body['ticket_promedio']['monto'] < 200_000_000
