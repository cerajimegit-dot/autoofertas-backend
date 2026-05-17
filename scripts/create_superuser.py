#!/usr/bin/env python
"""
Script to create a superuser for development
"""
import os
import sys
import django

# Add parent directory to path to find the Django project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import CustomUser, Enterprise

# Create test enterprise
print("Creating test enterprise...")
enterprise, created = Enterprise.objects.get_or_create(
    ruc='1234567-8',
    defaults={
        'name': 'Admin Enterprise',
        'subscription_status': 'active'
    }
)
if created:
    print(f"✓ Enterprise created: {enterprise.name}")
else:
    print(f"✓ Enterprise already exists: {enterprise.name}")

# Create superuser
print("Creating superuser...")
user, created = CustomUser.objects.get_or_create(
    email='admin@playas.py',
    defaults={
        'username': 'admin',
        'first_name': 'Admin',
        'last_name': 'User',
        'enterprise': enterprise,
        'role': 'admin',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True
    }
)

if created:
    user.set_password('admin123')
    user.save()
    print(f"✓ Superuser created:")
    print(f"  Email: {user.email}")
    print(f"  Password: admin123")
    print(f"  Enterprise: {user.enterprise.name}")
else:
    print(f"✓ Superuser already exists: {user.email}")

# Create test manager user
print("\nCreating test manager user...")
manager, created = CustomUser.objects.get_or_create(
    email='manager@playas.py',
    defaults={
        'username': 'manager',
        'first_name': 'Manager',
        'last_name': 'User',
        'enterprise': enterprise,
        'role': 'manager',
        'is_active': True
    }
)

if created:
    manager.set_password('manager123')
    manager.save()
    print(f"✓ Manager created:")
    print(f"  Email: {manager.email}")
    print(f"  Password: manager123")
else:
    print(f"✓ Manager already exists: {manager.email}")

print("\n✓ All users created successfully!")
