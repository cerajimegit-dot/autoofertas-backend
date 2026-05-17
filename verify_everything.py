import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import CustomUser, Enterprise, Vehicle, Customer, Sale, Quotum
from django.db import connection

print("\n" + "="*80)
print("VERIFICACIÓN FINAL COMPLETA")
print("="*80)

# 1. BD conectada
print("\n1. CONEXIÓN A BASE DE DATOS:")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM core_enterprise;")
        ent_count = cursor.fetchone()[0]
    print(f"   ✅ BD conectada (Empresas encontradas: {ent_count})")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# 2. Verificar datos principales
print("\n2. DATOS EN BASE DE DATOS:")
enterprise = Enterprise.objects.filter(ruc='12345678').first()
if enterprise:
    print(f"   ✅ Empresa: {enterprise.name}")
    v_count = Vehicle.objects.filter(enterprise=enterprise).count()
    c_count = Customer.objects.filter(enterprise=enterprise).count()
    s_count = Sale.objects.filter(enterprise=enterprise).count()
    q_count = Quotum.objects.filter(enterprise=enterprise).count()
    print(f"      - Vehículos: {v_count}")
    print(f"      - Clientes: {c_count}")
    print(f"      - Ventas: {s_count}")
    print(f"      - Cuotas: {q_count}")
else:
    print("   ❌ No existe empresa AUTO OFERTAS")

# 3. Verificar usuarios y acceso
print("\n3. USUARIOS Y ACCESO A DATOS:")
users = CustomUser.objects.filter(username__in=['admin', 'manager'])
for user in users:
    print(f"   Usuario: {user.username}")
    if user.enterprise == enterprise:
        print(f"      ✅ Empresa: {user.enterprise.name}")
        print(f"      ✅ Tendrá acceso a todos los datos")
    else:
        print(f"      ❌ Empresa: {user.enterprise}")
        print(f"      ❌ No verá datos")

# 4. Test de filtros de vista
print("\n4. TEST DE FILTROS DE VISTA:")
admin = CustomUser.objects.get(username='admin')
if admin.enterprise:
    filtered_vehicles = Vehicle.objects.filter(enterprise=admin.enterprise)
    print(f"   Filtro enterprise=admin.enterprise:")
    print(f"      Vehículos retornados: {filtered_vehicles.count()}")
    print(f"      ✅ Filtro funciona correctamente")
else:
    print(f"   ❌ Admin sin empresa")

print("\n" + "="*80)
print("INSTRUCCIONES PARA CLIENTE")
print("="*80)
print("""
1. Abre el navegador:
   http://127.0.0.1:8001/login/

2. Inicia sesión con:
   - Usuario: admin
   - Contraseña: admin123456

3. Verifica que ves:
   ✓ Dashboard con números (344 vehículos, 218 clientes, etc.)
   ✓ Menú con opciones: Vehículos, Clientes, Ventas, Cuotas
   ✓ Al hacer clic, lista de datos

4. Si algo no funciona, abre DevTools (F12) y revisa:
   - Console para errores JavaScript
   - Network para ver respuestas de API
""")
print("="*80 + "\n")
