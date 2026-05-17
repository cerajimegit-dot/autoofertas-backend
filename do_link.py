import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Brand, Vehicle, Enterprise

# Get first enterprise
ent = Enterprise.objects.first()

if ent:
    print(f"Linking to enterprise: {ent.name}")
    
    # Update orphaned brands
    orphan_brands = Brand.objects.filter(enterprise__isnull=True)
    count_brands = orphan_brands.count()
    orphan_brands.update(enterprise=ent)
    
    # Update orphaned vehicles
    orphan_vehicles = Vehicle.objects.filter(enterprise__isnull=True)
    count_vehicles = orphan_vehicles.count()
    orphan_vehicles.update(enterprise=ent)
    
    print(f"Updated {count_brands} brands and {count_vehicles} vehicles")
    print("SUCCESS")
else:
    print("ERROR: No enterprise found")
