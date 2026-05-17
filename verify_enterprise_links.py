#!/usr/bin/env python
"""
Final verification that all brands and vehicles are properly linked to enterprise
"""
import os
import sys
import django
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from core.models import Brand, Vehicle, Enterprise, Customer, Sale, Quotum

def verify_data():
    """Verify all data is properly associated with enterprise"""
    try:
        ent = Enterprise.objects.first()
        
        if not ent:
            print("ERROR: No enterprise found")
            return False
        
        print(f"Verification Report for Enterprise: {ent.name}")
        print("=" * 60)
        
        # Brands verification
        all_brands = Brand.objects.all().count()
        ent_brands = Brand.objects.filter(enterprise=ent).count()
        orphan_brands = Brand.objects.filter(enterprise__isnull=True).count()
        
        print("\nBrands:")
        print(f"  Total: {all_brands}")
        print(f"  Linked to {ent.name}: {ent_brands}")
        print(f"  Orphaned (no enterprise): {orphan_brands}")
        
        # Vehicles verification
        all_vehicles = Vehicle.objects.all().count()
        ent_vehicles = Vehicle.objects.filter(enterprise=ent).count()
        orphan_vehicles = Vehicle.objects.filter(enterprise__isnull=True).count()
        
        print("\nVehicles:")
        print(f"  Total: {all_vehicles}")
        print(f"  Linked to {ent.name}: {ent_vehicles}")
        print(f"  Orphaned (no enterprise): {orphan_vehicles}")
        
        # Additional data
        customers = Customer.objects.filter(enterprise=ent).count()
        sales = Sale.objects.filter(enterprise=ent).count()
        quotas = Quotum.objects.filter(enterprise=ent).count()
        
        print("\nOther Data:")
        print(f"  Customers: {customers}")
        print(f"  Sales: {sales}")
        print(f"  Quotas: {quotas}")
        
        # SQL verification
        conn = sqlite3.connect('db.sqlite3')
        c = conn.cursor()
        
        c.execute('''SELECT COUNT(*) FROM core_brand WHERE enterprise_id IS NULL''')
        sql_orphan_brands = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM core_vehicle WHERE enterprise_id IS NULL''')
        sql_orphan_vehicles = c.fetchone()[0]
        
        conn.close()
        
        print("\nSQL Direct Verification:")
        print(f"  Orphaned brands (NULL enterprise_id): {sql_orphan_brands}")
        print(f"  Orphaned vehicles (NULL enterprise_id): {sql_orphan_vehicles}")
        
        print("\n" + "=" * 60)
        
        if orphan_brands == 0 and orphan_vehicles == 0 and sql_orphan_brands == 0 and sql_orphan_vehicles == 0:
            print("SUCCESS: All data properly linked to enterprise")
            print("\nThe vehicles and brands you registered are now:")
            print(f"  - Related to the test account '{ent.name}'")
            print(f"  - Ready for dashboard and reporting")
            return True
        else:
            print("WARNING: Some data may still be orphaned")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = verify_data()
    sys.exit(0 if success else 1)
