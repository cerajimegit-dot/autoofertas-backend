import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import CustomUser, Enterprise

# Crear usuarios de prueba si no existen
print("CREANDO/VERIFICANDO USUARIOS...\n")

# Obtener empresa primera
enterprise = Enterprise.objects.first()
if not enterprise:
    print("ERROR: No hay empresas en el sistema")
    sys.exit(1)

print(f"Empresa por defecto: {enterprise.name} (RUC: {enterprise.ruc})\n")

# Crear admin
if not CustomUser.objects.filter(username='admin').exists():
    admin = CustomUser.objects.create_superuser(
        username='admin',
        email='admin@playa.com',
        password='admin123456',
        role='admin'
    )
    admin.enterprises.add(enterprise)
    print("✓ Usuario 'admin' creado (contraseña: admin123456)")
else:
    print("✓ Usuario 'admin' ya existe")
    admin = CustomUser.objects.get(username='admin')
    if not admin.enterprises.exists():
        admin.enterprises.add(enterprise)
        print("  - Vinculado a empresa")

# Crear manager
if not CustomUser.objects.filter(username='manager').exists():
    manager = CustomUser.objects.create_user(
        username='manager',
        email='manager@playa.com',
        password='manager123456',
        role='manager',
        is_staff=True
    )
    manager.enterprises.add(enterprise)
    print("✓ Usuario 'manager' creado (contraseña: manager123456)")
else:
    print("✓ Usuario 'manager' ya existe")
    manager = CustomUser.objects.get(username='manager')
    if not manager.enterprises.exists():
        manager.enterprises.add(enterprise)
        print("  - Vinculado a empresa")

# Crear vendedor
if not CustomUser.objects.filter(username='vendor').exists():
    vendor = CustomUser.objects.create_user(
        username='vendor',
        email='vendor@playa.com',
        password='vendor123456',
        role='vendor',
        is_staff=False
    )
    vendor.enterprises.add(enterprise)
    print("✓ Usuario 'vendor' creado (contraseña: vendor123456)")
else:
    print("✓ Usuario 'vendor' ya existe")
    vendor = CustomUser.objects.get(username='vendor')
    if not vendor.enterprises.exists():
        vendor.enterprises.add(enterprise)
        print("  - Vinculado a empresa")

print("\n" + "="*60)
print("USUARIOS DISPONIBLES PARA INICIAR SESION:")
print("="*60)
print("\n1. admin / admin123456 (Administrador)")
print("2. manager / manager123456 (Gerente)")
print("3. vendor / vendor123456 (Vendedor)")
print("\nEmpresa: AUTO OFERTAS")
print("="*60)
