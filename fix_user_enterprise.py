import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import CustomUser, Enterprise

print("\n" + "="*70)
print("REASIGNANDO USUARIOS A EMPRESA CON DATOS")
print("="*70 + "\n")

# Obtener empresa con datos
auto_ofertas = Enterprise.objects.filter(ruc='12345678').first()
if not auto_ofertas:
    print("❌ No se encontró empresa AUTO OFERTAS (RUC: 12345678)")
    sys.exit(1)

print(f"Empresa destino: {auto_ofertas.name}")
print(f"  ├─ Vehículos: {auto_ofertas.vehicles.count()}")
print(f"  ├─ Clientes: {auto_ofertas.customers.count()}")
print(f"  ├─ Ventas: {auto_ofertas.sales.count()}")
print(f"  └─ Cuotas: {auto_ofertas.quotas.count()}\n")

# Reasignar usuarios principales
users_to_fix = ['admin', 'manager']

for username in users_to_fix:
    user = CustomUser.objects.filter(username=username).first()
    if user:
        old_enterprise = user.enterprise
        user.enterprise = auto_ofertas
        user.save()
        print(f"✓ Usuario '{username}':")
        print(f"  Anterior: {old_enterprise}")
        print(f"  Nuevo: {auto_ofertas.name}\n")
    else:
        print(f"✗ Usuario '{username}' no existe\n")

print("="*70)
print("Reasignación completada ✅")
print("="*70)
print("\nAhora prueba con:")
print("  - Usuario: admin / Contraseña: admin123456")
print("  - O Usuario: manager / Contraseña: manager123456")
