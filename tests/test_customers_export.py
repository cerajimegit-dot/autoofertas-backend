"""Tests del endpoint /api/customers/export/."""

import pytest
from rest_framework.test import APIClient

from core.models import CustomUser, Enterprise, Customer


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    e1 = Enterprise.objects.create(name='E1', ruc='1', email='e@x.com',
                                    phone='1', address='x', city='x')
    e2 = Enterprise.objects.create(name='E2', ruc='2', email='e2@x.com',
                                    phone='2', address='y', city='y')
    Customer.objects.create(
        enterprise=e1, first_name='Mati', last_name='Pérez',
        document_type='ci', document_number='123', email='m@x.com',
        phone='0', city='Asunción',
    )
    Customer.objects.create(
        enterprise=e1, first_name='Marce', last_name='Ortiz',
        document_type='ci', document_number='456', email='ma@x.com',
        phone='0', city='Asunción',
    )
    # E2 — no debe aparecer
    Customer.objects.create(
        enterprise=e2, first_name='SECRETO', last_name='OTRA',
        document_type='ci', document_number='999', email='s@x.com',
        phone='0', city='Asunción',
    )
    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client}


def test_bom_y_filename(setup):
    r = setup['client'].get('/api/customers/export/')
    assert r.status_code == 200
    assert r.content.startswith('﻿'.encode('utf-8'))
    assert 'clientes_' in r['Content-Disposition']


def test_filas_y_tenancy(setup):
    r = setup['client'].get('/api/customers/export/')
    body = r.content.decode('utf-8')
    assert 'Mati' in body
    assert 'Marce' in body
    assert 'SECRETO' not in body


def test_delimitador_coma(setup):
    r = setup['client'].get('/api/customers/export/?delimiter=comma')
    body = r.content.decode('utf-8').lstrip('﻿')
    first_line = body.splitlines()[0]
    assert first_line.startswith('ID,Nombre,Apellido')
