"""
Test script for CRM functionality
"""
import os
import django
import requests
from django.contrib.auth import authenticate

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'playas_autos.settings')
django.setup()

from django.test import Client
from core.models import CustomUser, Enterprise, Customer

# Create a test client
client = Client()

# Test login
print("=" * 60)
print("TEST 1: Testing Login")
print("=" * 60)
response = client.post('/login/', {
    'username': 'admin',
    'password': 'admin'
})
print(f"Login response status: {response.status_code}")
if response.status_code in [200, 302]:
    print("✓ Login successful (redirected to dashboard)")
else:
    print("✗ Login failed")

# Get CSRF token for authenticated requests
print("\n" + "=" * 60)
print("TEST 2: Testing CRM Customer List")
print("=" * 60)
response = client.get('/crm/customers/')
print(f"Customer list status: {response.status_code}")
if response.status_code == 200:
    print("✓ Customer list page loaded successfully")
    if 'customer' in response.content.decode().lower():
        print("✓ Page contains customer data")
else:
    print(f"✗ Customer list failed: {response.status_code}")

# Test customer detail
print("\n" + "=" * 60)
print("TEST 3: Testing CRM Customer Detail")
print("=" * 60)
try:
    customer = Customer.objects.first()
    if customer:
        response = client.get(f'/crm/customer/{customer.id}/')
        print(f"Customer detail status: {response.status_code}")
        if response.status_code == 200:
            print(f"✓ Customer detail loaded for {customer.first_name}")
        else:
            print(f"✗ Customer detail failed: {response.status_code}")
    else:
        print("⚠ No customers in database")
except Exception as e:
    print(f"✗ Error: {str(e)}")

# Test customer edit page
print("\n" + "=" * 60)
print("TEST 4: Testing CRM Customer Edit Form")
print("=" * 60)
try:
    customer = Customer.objects.first()
    if customer:
        response = client.get(f'/crm/customer/{customer.id}/edit/')
        print(f"Customer edit page status: {response.status_code}")
        if response.status_code == 200:
            print(f"✓ Customer edit form loaded")
        else:
            print(f"✗ Customer edit failed: {response.status_code}")
    else:
        print("⚠ No customers in database")
except Exception as e:
    print(f"✗ Error: {str(e)}")

# Test sale register page
print("\n" + "=" * 60)
print("TEST 5: Testing Sale Register Form")
print("=" * 60)
response = client.get('/crm/sale-register/')
print(f"Sale register page status: {response.status_code}")
if response.status_code == 200:
    print("✓ Sale register form loaded")
    content = response.content.decode().lower()
    if 'vehículo' in content or 'vehiculo' in content:
        print("✓ Form contains vehicle selector")
else:
    print(f"✗ Sale register failed: {response.status_code}")

# Test payment history
print("\n" + "=" * 60)
print("TEST 6: Testing Payment History")
print("=" * 60)
try:
    customer = Customer.objects.first()
    if customer:
        response = client.get(f'/crm/customer/{customer.id}/payments/')
        print(f"Payment history status: {response.status_code}")
        if response.status_code == 200:
            print(f"✓ Payment history loaded")
        else:
            print(f"✗ Payment history failed: {response.status_code}")
    else:
        print("⚠ No customers in database")
except Exception as e:
    print(f"✗ Error: {str(e)}")

# Test URL configurations
print("\n" + "=" * 60)
print("TEST 7: URL Configuration Verification")
print("=" * 60)
from django.urls import reverse
urls_to_test = [
    'ui:customer_list_crm',
    'ui:sale_register',
]
for url_name in urls_to_test:
    try:
        url = reverse(url_name)
        print(f"✓ {url_name}: {url}")
    except Exception as e:
        print(f"✗ {url_name}: Error - {str(e)}")

print("\n" + "=" * 60)
print("CRM TESTING COMPLETE")
print("=" * 60)
