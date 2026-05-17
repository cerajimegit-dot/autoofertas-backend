import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Vehicle, Customer, Sale, Quotum
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

print("\n" + "="*70)
print("VERIFICACIÓN FINAL: USUARIOS Y DATOS ACCESIBLES")
print("="*70 + "\n")

admin = User.objects.filter(username='admin').first()
manager = User.objects.filter(username='manager').first()

for user in [admin, manager]:
    if not user:
        continue
    
    print(f"Usuario: {user.username}")
    print(f"  Email: {user.email}")
    print(f"  Empresa: {user.enterprise}")
    
    if user.enterprise:
        vehicles = Vehicle.objects.filter(enterprise=user.enterprise).count()
        customers = Customer.objects.filter(enterprise=user.enterprise).count()
        sales = Sale.objects.filter(enterprise=user.enterprise).count()
        quotas = Quotum.objects.filter(enterprise=user.enterprise).count()
        
        print(f"  Datos visibles:")
        print(f"    ├─ Vehículos: {vehicles}")
        print(f"    ├─ Clientes: {customers}")
        print(f"    ├─ Ventas: {sales}")
        print(f"    └─ Cuotas: {quotas}")
        
        if vehicles > 0 and customers > 0 and sales > 0:
            print(f"  ✅ LISTO PARA USAR")
        else:
            print(f"  ⚠️  DATOS INCOMPLETOS")
    else:
        print(f"  ❌ SIN EMPRESA ASIGNADA")
    
    print()

print("="*70)
print("INSTRU CCIONES:")
print("="*70)
print("\n1. Ve a: http://127.0.0.1:8001/login/")
print("2. Inicia sesión con:")
print("   - Usuario: admin")
print("   - Contraseña: admin123456")
print("\n3. Deberías ver:")
print("   - Dashboard con datos")
print("   - Listado de vehículos")
print("   - Listado de clientes")
print("   - Listado de ventas")
print("   - Listado de cuotas")
print("\n" + "="*70)
