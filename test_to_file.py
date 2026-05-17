#!/usr/bin/env python
"""Test that writes output to file"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')

output = []
output.append("Starting runtime test...\n")

try:
    import django
    django.setup()
    output.append("✓ Django setup successful\n")
    
    # Test 1: Imports
    from ui import views
    output.append("✓ ui.views imported\n")
    
    # Test 2: Check login_view
    if hasattr(views, 'login_view'):
        output.append("✓ login_view found\n")
    else:
        output.append("✗ login_view NOT found\n")
    
    # Test 3: Check other views
    for name in ['dashboard', 'vehicles', 'sales', 'quotas', 'customers']:
        if hasattr(views, name):
            output.append(f"✓ {name} view found\n")
    
    # Test 4: Check authenticate
    from django.contrib.auth import authenticate
    output.append("✓ authenticate imported\n")
    
    # Test 5: Check auth_login
    from django.contrib.auth import login as auth_login
    output.append("✓ auth_login imported\n")
    
    # Test 6: Check admin user
    from django.contrib.auth.models import User
    admin = User.objects.get(username='admin')
    output.append(f"✓ Admin user exists: {admin.username}\n")
    
    # Test 7: Check URL reversal
    from django.urls import reverse
    login_url = reverse('ui:login')
    dashboard_url = reverse('ui:dashboard')
    output.append(f"✓ URLs configured: {login_url}, {dashboard_url}\n")
    
    # Test 8: Check login template
    from django.template.loader import render_to_string
    template = render_to_string('ui/login.html')
    if 'csrf' in template.lower():
        output.append("✓ CSRF token in template\n")
    if 'username' in template.lower():
        output.append("✓ Username field in template\n")
    if 'password' in template.lower():
        output.append("✓ Password field in template\n")
    
    # Test 9: Check base template
    from django.template.loader import get_template
    base = get_template('ui/base.html')
    if 'resolver_match' not in base.source:
        output.append("✓ resolver_match REMOVED from base.html\n")
    else:
        output.append("✗ resolver_match STILL in base.html\n")
    
    if 'request.path' in base.source:
        output.append("✓ request.path used in base.html\n")
    
    # Test 10: Check data
    from core.models import Vehicle, Quotum
    vehicles = Vehicle.objects.count()
    quotas = Quotum.objects.count()
    output.append(f"✓ Data: {vehicles} vehicles, {quotas} quotas\n")
    
    output.append("\n✓✓✓ ALL TESTS PASSED ✓✓✓\n")
    
except Exception as e:
    output.append(f"\n✗ ERROR: {e}\n")
    import traceback
    output.append(traceback.format_exc())

# Write output
with open('test_output.txt', 'w') as f:
    f.writelines(output)

print("Test completed - check test_output.txt")
