import pytest
from django.contrib.auth import get_user_model
from core.models import Enterprise, Branch

User = get_user_model()


@pytest.fixture
def test_enterprise(db):
    """Fixture para crear una empresa de prueba"""
    return Enterprise.objects.create(
        name='Test Enterprise',
        ruc='80000000',
        email='test@enterprise.com',
        phone='+595971234567',
        address='Test Address',
        city='Asunción'
    )


@pytest.fixture
def test_branch(db, test_enterprise):
    """Fixture para crear una sucursal de prueba"""
    return Branch.objects.create(
        enterprise=test_enterprise,
        name='Test Branch',
        code='TB001',
        address='Test Branch Address',
        city='Asunción',
        phone='+595971234567'
    )


@pytest.fixture
def test_admin_user(db, test_enterprise):
    """Fixture para crear un usuario administrador de prueba"""
    return User.objects.create_user(
        username='admintest',
        email='admin@test.com',
        password='testpass123',
        enterprise=test_enterprise,
        role='admin'
    )


@pytest.fixture
def test_manager_user(db, test_enterprise, test_branch):
    """Fixture para crear un usuario encargado de prueba"""
    user = User.objects.create_user(
        username='managertest',
        email='manager@test.com',
        password='testpass123',
        enterprise=test_enterprise,
        role='manager'
    )
    test_branch.manager = user
    test_branch.save()
    return user


@pytest.fixture
def test_vendor_user(db, test_enterprise):
    """Fixture para crear un usuario vendedor de prueba"""
    return User.objects.create_user(
        username='vendortest',
        email='vendor@test.com',
        password='testpass123',
        enterprise=test_enterprise,
        role='vendor'
    )
