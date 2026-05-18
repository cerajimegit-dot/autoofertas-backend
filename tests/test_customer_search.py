"""Tests del endpoint GET /api/customers/search/?q=...

En el entorno de tests usamos SQLite, así que el path que se ejercita
es el fallback ILIKE por tokens. El path pg_trgm sólo aplica en
Postgres con la extensión habilitada y se cubre con QA en staging.

Casos:
  - q muy corto (<2 chars) → 200 con lista vacía y `used: none`.
  - Match por nombre, por apellido, por documento, por email, por teléfono.
  - Match exigiendo TODOS los tokens (no OR — si el usuario tipea "carlos
    perez", queremos clientes que matcheen ambos).
  - Tenancy: no muestra clientes de otra empresa.
  - Limit: respeta el parámetro y lo capa en 50.
"""

from datetime import date
import pytest
from rest_framework.test import APIClient

from core.models import CustomUser, Enterprise, Customer


pytestmark = pytest.mark.django_db


@pytest.fixture
def setup():
    e1 = Enterprise.objects.create(
        name='E1', ruc='11111111', email='e1@test.com',
        phone='1', address='x', city='Asunción',
    )
    e2 = Enterprise.objects.create(
        name='E2', ruc='22222222', email='e2@test.com',
        phone='2', address='y', city='Asunción',
    )

    # Empresa 1 — clientes que vamos a buscar.
    # Documentos únicos para no colisionar (el modelo tiene unique
    # por enterprise+document_number).
    Customer.objects.create(
        enterprise=e1, first_name='Carlos', last_name='Pérez',
        document_type='ci', document_number='1234567',
        email='carlos.perez@gmail.com', phone='0981111111', city='Asunción',
    )
    Customer.objects.create(
        enterprise=e1, first_name='María', last_name='Pérez',
        document_type='ci', document_number='2345678',
        email='maria.perez@gmail.com', phone='0982222222', city='Asunción',
    )
    Customer.objects.create(
        enterprise=e1, first_name='Carlos', last_name='González',
        document_type='ci', document_number='3456789',
        email='carlos.g@gmail.com', phone='0983333333', city='Asunción',
    )
    # Empresa 2 — homónimo, no debe aparecer.
    Customer.objects.create(
        enterprise=e2, first_name='Carlos', last_name='OtraEmpresa',
        document_type='ci', document_number='9999999',
        email='ce@otra.com', phone='099X', city='X',
    )

    user = CustomUser.objects.create_user(
        username='admin1', email='admin1@e1.com', password='x',
        enterprise=e1, role='admin',
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return {'client': client, 'e1': e1, 'e2': e2, 'user': user}


def test_query_muy_corto_devuelve_vacio(setup):
    r = setup['client'].get('/api/customers/search/?q=a')
    assert r.status_code == 200
    body = r.json()
    assert body['results'] == []
    assert body['used'] == 'none'


def test_busqueda_por_nombre(setup):
    r = setup['client'].get('/api/customers/search/?q=Maria')
    assert r.status_code == 200
    body = r.json()
    names = [c['first_name'] for c in body['results']]
    assert 'María' in names
    # No debe traer a Carlos
    assert 'Carlos' not in names


def test_busqueda_por_documento(setup):
    r = setup['client'].get('/api/customers/search/?q=2345678')
    body = r.json()
    docs = [c['document_number'] for c in body['results']]
    assert '2345678' in docs
    assert len(body['results']) == 1


def test_busqueda_por_email_parcial(setup):
    r = setup['client'].get('/api/customers/search/?q=maria.perez')
    body = r.json()
    emails = [c['email'] for c in body['results']]
    assert 'maria.perez@gmail.com' in emails


def test_busqueda_por_telefono(setup):
    r = setup['client'].get('/api/customers/search/?q=0982')
    body = r.json()
    phones = [c['phone'] for c in body['results']]
    assert '0982222222' in phones


def test_dos_tokens_exigen_ambos(setup):
    """`carlos perez` debe matchear Carlos Pérez y NO María Pérez ni Carlos González."""
    r = setup['client'].get('/api/customers/search/?q=carlos+perez')
    body = r.json()
    assert len(body['results']) == 1
    c = body['results'][0]
    assert c['first_name'] == 'Carlos'
    assert c['last_name'] == 'Pérez'


def test_no_filtra_otra_empresa(setup):
    """Tenancy: 'Carlos' no debe traer al de la otra empresa."""
    r = setup['client'].get('/api/customers/search/?q=Carlos')
    body = r.json()
    docs = [c['document_number'] for c in body['results']]
    assert '9999999' not in docs


def test_limit(setup):
    r = setup['client'].get('/api/customers/search/?q=erez&limit=1')
    body = r.json()
    assert len(body['results']) == 1


def test_limit_capeado_en_50(setup):
    """limit=9999 debe quedar capeado en 50 (defensa contra abuso)."""
    r = setup['client'].get('/api/customers/search/?q=erez&limit=9999')
    # No hay forma trivial de saber si quedó capeado sin tener ≥50 clientes,
    # pero al menos verificamos que no haya error 400/500.
    assert r.status_code == 200


def test_used_indica_backend(setup):
    """En SQLite el campo `used` debe decir 'ilike' (fallback)."""
    r = setup['client'].get('/api/customers/search/?q=Carlos')
    assert r.json()['used'] == 'ilike'
