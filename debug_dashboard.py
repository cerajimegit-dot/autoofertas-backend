#!/usr/bin/env python
"""
Check Django dashboard error details
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from ui.views import dashboard

# Create a mock request with authenticated user
factory = RequestFactory()
request = factory.get('/dashboard/')

# Get or create the admin user
try:
    user = User.objects.get(username='admin')
    request.user = user
    print(f"✓ Found user: {user.username}")
except User.DoesNotExist:
    print("✗ Admin user not found!")
    sys.exit(1)

# Try to render the dashboard
try:
    response = dashboard(request)
    print(f"✓ Dashboard view executed: Status {response.status_code}")
    print(f"  Content length: {len(response.content)} bytes")
except Exception as e:
    print(f"✗ Error in dashboard view:")
    print(f"  {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
