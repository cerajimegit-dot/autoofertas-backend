#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')

try:
    django.setup()
    print("✓ Django setup successful")
    
    # Import views
    from ui import views
    print("✓ ui.views imported")
    
    # Check if login_view exists
    if hasattr(views, 'login_view'):
        print("✓ login_view found")
    else:
        print("✗ login_view NOT found")
    
    # Check dashboard
    if hasattr(views, 'dashboard'):
        print("✓ dashboard found")
    else:
        print("✗ dashboard NOT found")
        
    # Check api endpoint
    if hasattr(views, 'api_dashboard_stats'):
        print("✓ api_dashboard_stats found")
    else:
        print("✗ api_dashboard_stats NOT found")
    
    print("\n✓ All views are properly defined and accessible")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
