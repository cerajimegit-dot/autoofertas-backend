import os
import sys
import django
from django.conf import settings

# Add parent directory to path to find the Django project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Enterprise, CustomUser
from django.contrib.auth import get_user_model

User = get_user_model()


def create_test_data():
    """Crear datos de prueba para desarrollo"""
    
    # Crear empresa de prueba
    try:
        enterprise = Enterprise.objects.create(
            name='Playas Test S.A.',
            ruc='80000000',
            email='test@playastest.com',
            phone='+595971234567',
            address='Calle Principal 123',
            city='Asunción',
            subscription_status='active'
        )
        print(f"✓ Empresa creada: {enterprise.name}")
    except Exception as e:
        print(f"✗ Error creando empresa: {e}")
        enterprise = Enterprise.objects.first()
    
    # Crear superusuario
    try:
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@playastest.com',
                password='admin123456',
                enterprise=enterprise,
                role='admin'
            )
            print(f"✓ Superusuario creado: {admin_user.username}")
        else:
            print("✗ Superusuario 'admin' ya existe")
    except Exception as e:
        print(f"✗ Error creando superusuario: {e}")
    
    # Crear usuarios de prueba
    try:
        if not User.objects.filter(username='manager1').exists():
            manager = User.objects.create_user(
                username='manager1',
                email='manager@playastest.com',
                password='manager123456',
                enterprise=enterprise,
                role='manager',
                is_staff=True
            )
            print(f"✓ Encargado creado: {manager.username}")
        else:
            print("✗ Usuario 'manager1' ya existe")
    except Exception as e:
        print(f"✗ Error creando manager: {e}")
    
    try:
        if not User.objects.filter(username='vendor1').exists():
            vendor = User.objects.create_user(
                username='vendor1',
                email='vendor@playastest.com',
                password='vendor123456',
                enterprise=enterprise,
                role='vendor'
            )
            print(f"✓ Vendedor creado: {vendor.username}")
        else:
            print("✗ Usuario 'vendor1' ya existe")
    except Exception as e:
        print(f"✗ Error creando vendor: {e}")


if __name__ == '__main__':
    print("Creando datos de prueba...")
    create_test_data()
    print("¡Datos de prueba creados exitosamente!")
