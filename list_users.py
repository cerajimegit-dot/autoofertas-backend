import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import CustomUser, Enterprise

print("=" * 60)
print("USUARIOS DISPONIBLES EN EL SISTEMA")
print("=" * 60)

users = CustomUser.objects.all()
print(f"\nTotal de usuarios: {users.count()}\n")

for user in users:
    print(f"Username: {user.username}")
    print(f"  Email: {user.email}")
    print(f"  Is Staff: {user.is_staff}")
    print(f"  Is Superuser: {user.is_superuser}")
    
    enterprises = user.enterprises.all()
    print(f"  Empresas asociadas: {enterprises.count()}")
    for enterprise in enterprises:
        print(f"    - {enterprise.name} (RUC: {enterprise.ruc})")
    print()

print("\n" + "=" * 60)
print("EMPRESAS EN EL SISTEMA")
print("=" * 60)

enterprises = Enterprise.objects.all()
print(f"\nTotal de empresas: {enterprises.count()}\n")

for enterprise in enterprises:
    print(f"Empresa: {enterprise.name}")
    print(f"  RUC: {enterprise.ruc}")
    print(f"  Usuarios: {enterprise.users.count()}")
    for user in enterprise.users.all():
        print(f"    - {user.username}")
    print()
