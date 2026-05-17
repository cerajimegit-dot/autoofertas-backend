import pytest
from django.test import TestCase
from core.models import CustomUser, Enterprise, Branch


pytestmark = pytest.mark.django_db


class TestCustomUserModel(TestCase):
    """Tests para el modelo CustomUser"""
    
    def setUp(self):
        self.enterprise = Enterprise.objects.create(
            name='Test Enterprise',
            ruc='80000000',
            email='test@enterprise.com',
            phone='+595971234567',
            address='Test Address',
            city='Asunción'
        )
    
    def test_create_admin_user(self):
        """Prueba crear usuario administrador"""
        user = CustomUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            enterprise=self.enterprise,
            role='admin'
        )
        assert user.role == 'admin'
        assert user.username == 'admin'
        assert user.enterprise == self.enterprise
    
    def test_create_manager_user(self):
        """Prueba crear usuario encargado"""
        user = CustomUser.objects.create_user(
            username='manager',
            email='manager@test.com',
            password='testpass123',
            enterprise=self.enterprise,
            role='manager'
        )
        assert user.role == 'manager'
    
    def test_create_vendor_user(self):
        """Prueba crear usuario vendedor"""
        user = CustomUser.objects.create_user(
            username='vendor',
            email='vendor@test.com',
            password='testpass123',
            enterprise=self.enterprise,
            role='vendor'
        )
        assert user.role == 'vendor'
    
    def test_user_string_representation(self):
        """Prueba la representación en string del usuario"""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            enterprise=self.enterprise,
            role='vendor'
        )
        assert str(user) == 'Test User (Vendedor)'


class TestEnterpriseModel(TestCase):
    """Tests para el modelo Enterprise"""
    
    def test_create_enterprise(self):
        """Prueba crear una empresa"""
        enterprise = Enterprise.objects.create(
            name='Test Company',
            ruc='80000001',
            email='company@test.com',
            phone='+595971234567',
            address='Test Address',
            city='Asunción'
        )
        assert enterprise.name == 'Test Company'
        assert enterprise.ruc == '80000001'
        assert enterprise.subscription_status == 'active'
    
    def test_enterprise_unique_ruc(self):
        """Prueba que RUC sea único"""
        Enterprise.objects.create(
            name='Company 1',
            ruc='80000001',
            email='company1@test.com',
            phone='+595971234567',
            address='Address 1',
            city='Asunción'
        )
        
        with pytest.raises(Exception):
            Enterprise.objects.create(
                name='Company 2',
                ruc='80000001',  # Este RUC ya existe
                email='company2@test.com',
                phone='+595971234567',
                address='Address 2',
                city='Asunción'
            )


class TestBranchModel(TestCase):
    """Tests para el modelo Branch"""
    
    def setUp(self):
        self.enterprise = Enterprise.objects.create(
            name='Test Enterprise',
            ruc='80000000',
            email='test@enterprise.com',
            phone='+595971234567',
            address='Test Address',
            city='Asunción'
        )
    
    def test_create_branch(self):
        """Prueba crear una sucursal"""
        branch = Branch.objects.create(
            enterprise=self.enterprise,
            name='Test Branch',
            code='TB001',
            address='Branch Address',
            city='Asunción',
            phone='+595971111111'
        )
        assert branch.name == 'Test Branch'
        assert branch.code == 'TB001'
        assert branch.is_active is True
    
    def test_unique_branch_code_per_enterprise(self):
        """Prueba que el código de sucursal sea único por empresa"""
        Branch.objects.create(
            enterprise=self.enterprise,
            name='Branch 1',
            code='B001',
            address='Address 1',
            city='Asunción',
            phone='+595971111111'
        )
        
        with pytest.raises(Exception):
            Branch.objects.create(
                enterprise=self.enterprise,
                name='Branch 2',
                code='B001',  # Código duplicado en la misma empresa
                address='Address 2',
                city='Asunción',
                phone='+595971111111'
            )
