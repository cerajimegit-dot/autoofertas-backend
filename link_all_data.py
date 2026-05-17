#!/usr/bin/env python
"""
Link orphaned brands and vehicles to the test enterprise
"""
import os
import sys
import django
import sqlite3

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Brand, Vehicle, Enterprise

def link_enterprise_data():
    """Link all orphaned brands and vehicles to the first enterprise"""
    try:
        # Get first enterprise
        ent = Enterprise.objects.first()
        
        if not ent:
            print("ERROR: No enterprise found in database")
            return False
        
        print(f"Enterprise found: {ent.name} (RUC: {ent.ruc})")
        
        # Count orphaned brands
        orphan_brands_qs = Brand.objects.filter(enterprise__isnull=True)
        orphan_brands_count = orphan_brands_qs.count()
        
        # Count orphaned vehicles
        orphan_vehicles_qs = Vehicle.objects.filter(enterprise__isnull=True)
        orphan_vehicles_count = orphan_vehicles_qs.count()
        
        print(f"\nBefore linking:")
        print(f"  Orphaned brands: {orphan_brands_count}")
        print(f"  Orphaned vehicles: {orphan_vehicles_count}")
        
        # Link brands
        if orphan_brands_count > 0:
            orphan_brands_qs.update(enterprise=ent)
            print(f"\nLinked {orphan_brands_count} brands to {ent.name}")
        
        # Link vehicles
        if orphan_vehicles_count > 0:
            orphan_vehicles_qs.update(enterprise=ent)
            print(f"Linked {orphan_vehicles_count} vehicles to {ent.name}")
        
        # Verify with ORM
        all_brands = Brand.objects.count()
        linked_brands = Brand.objects.filter(enterprise=ent).count()
        
        all_vehicles = Vehicle.objects.count()
        linked_vehicles = Vehicle.objects.filter(enterprise=ent).count()
        
        print(f"\nAfter linking:")
        print(f"  Total brands: {all_brands} (linked to {ent.name}: {linked_brands})")
        print(f"  Total vehicles: {all_vehicles} (linked to {ent.name}: {linked_vehicles})")
        
        # Final check with raw SQL
        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM core_brand WHERE enterprise_id IS NULL')
        orphan_brands_check = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id IS NULL')
        orphan_vehicles_check = c.fetchone()[0]
        
        conn.close()
        
        print(f"\nSQL verification:")
        print(f"  Remaining orphaned brands: {orphan_brands_check}")
        print(f"  Remaining orphaned vehicles: {orphan_vehicles_check}")
        
        if orphan_brands_check == 0 and orphan_vehicles_check == 0:
            print("\n✓ SUCCESS: All data properly linked to enterprise")
            return True
        else:
            print("\n✗ WARNING: Some data still orphaned after linking")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = link_enterprise_data()
    sys.exit(0 if success else 1)
