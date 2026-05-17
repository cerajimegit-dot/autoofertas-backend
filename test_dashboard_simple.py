#!/usr/bin/env python
"""
Test login and dashboard with proper session management
"""
import requests
import sys

BASE_URL = "http://localhost:8001"
SESSION = requests.Session()

print("=" * 70)
print("Testing Login and Dashboard Access with Session Management")
print("=" * 70)

# Step 1: GET login page
print("\n[1] GET /login/ page...")
try:
    r = SESSION.get(f"{BASE_URL}/login/", timeout=5)
    print(f"    Status: {r.status_code}")
    if r.status_code != 200:
        print(f"    ERROR: Unexpected status code")
        sys.exit(1)
    print("    ✓ Login page retrieved")
except Exception as e:
    print(f"    ERROR: {e}")
    sys.exit(1)

# Step 2: Extract CSRF token
print("\n[2] Extract CSRF token from login page...")
import re
csrf_match = re.search(r'csrfmiddlewaretoken["\']?\s*value=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
if not csrf_match:
    print("    ERROR: CSRF token not found")
    print("    First 500 chars of response:")
    print("    " + r.text[:500].replace("\n", "\n    "))
    sys.exit(1)

csrf_token = csrf_match.group(1)
print(f"    ✓ CSRF token: {csrf_token[:30]}...")

# Step 3: POST login
print("\n[3] POST login with credentials...")
login_data = {
    'username': 'admin',
    'password': 'admin123',
    'csrfmiddlewaretoken': csrf_token
}

try:
    r = SESSION.post(
        f"{BASE_URL}/login/",
        data=login_data,
        timeout=5,
        allow_redirects=False
    )
    print(f"    Status: {r.status_code}")
    
    if r.status_code in [301, 302, 303]:
        location = r.headers.get('Location', '')
        print(f"    ✓ Redirect to: {location}")
        
        # Follow the redirect
        if 'dashboard' in location:
            dashboard_url = f"{BASE_URL}{location}" if location.startswith('/') else location
            print(f"\n[4] GET dashboard at {dashboard_url}...")
            r = SESSION.get(dashboard_url, timeout=5)
            print(f"    Status: {r.status_code}")
            
            if r.status_code == 200:
                print("    ✓ Dashboard loaded successfully")
                # Check if dashboard content is present
                if 'Dashboard' in r.text or 'Vehículos' in r.text:
                    print("    ✓ Dashboard content is present")
                else:
                    print("    ⚠ Dashboard template might not be rendering correctly")
                    print("    First 1000 chars:")
                    print("    " + r.text[:1000].replace("\n", "\n    "))
            elif r.status_code >= 500:
                print(f"    ✗ Server error")
                print("    Response preview:")
                print("    " + r.text[:2000].replace("\n", "\n    "))
            else:
                print(f"    ⚠ Unexpected status code")
                
    elif r.status_code == 200:
        print("    ⚠ Login returned 200 (form re-displayed)")
        if 'Usuario o contraseña inválidos' in r.text:
            print("    ERROR: Invalid credentials error message")
        else:
            print("    ERROR: Login failed without error message")
        print("\n    First 500 chars of response:")
        print("    " + r.text[:500].replace("\n", "\n    "))
    else:
        print(f"    ✗ Unexpected status code: {r.status_code}")
        print("    Response preview:")
        print("    " + r.text[:1000].replace("\n", "\n    "))
        
except Exception as e:
    print(f"    ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("Test completed")
print("=" * 70)
