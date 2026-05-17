import requests
import time
import re

time.sleep(2)  # Wait for server

try:
    # Test login flow
    s = requests.Session()
    
    # Get login page
    r = s.get('http://localhost:8001/login/', timeout=5)
    print(f"Login page: {r.status_code}")
    
    if r.status_code != 200:
        print("ERROR: Could not get login page")
        exit(1)
    
    # Extract CSRF
    m = re.search(r'csrfmiddlewaretoken["\']?\s*value=["\']([^"\']+)["\']', r.text, re.IGNORECASE)
    if not m:
        print("ERROR: CSRF token not found")
        exit(1)
    
    csrf = m.group(1)
    print(f"CSRF token found: {csrf[:20]}...")
    
    # Login
    r = s.post('http://localhost:8001/login/', 
               data={'username': 'admin', 'password': 'admin123', 'csrfmiddlewaretoken': csrf},
               allow_redirects=False,
               timeout=5)
    print(f"Login POST: {r.status_code}")
    
    if r.status_code in [301, 302]:
        print(f"Redirect: {r.headers.get('Location', 'N/A')}")
        
        # Get dashboard
        r = s.get('http://localhost:8001/dashboard/', timeout=5)
        print(f"Dashboard: {r.status_code}")
        
        if r.status_code == 200:
            print("✓ SUCCESS: Login and dashboard working!")
        else:
            print(f"✗ Dashboard error: {r.status_code}")
            print("First 500 chars:", r.text[:500])
    else:
        print(f"✗ Login failed with status {r.status_code}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
