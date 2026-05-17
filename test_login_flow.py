#!/usr/bin/env python
"""
Test script to verify login form is working correctly with CSRF protection
"""
import requests
import re
import sys

BASE_URL = "http://localhost:8001"

def test_login_flow():
    """Test the complete login flow"""
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("=" * 60)
    print("Testing Login Flow")
    print("=" * 60)
    
    # Step 1: GET login page to retrieve CSRF token
    print("\n[1] GET /login/ to retrieve CSRF token...")
    try:
        response = session.get(f"{BASE_URL}/login/")
        print(f"    Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"    ERROR: Expected 200, got {response.status_code}")
            return False
            
    except Exception as e:
        print(f"    ERROR: {e}")
        return False
    
    # Parse HTML to extract CSRF token using regex
    try:
        match = re.search(r'name=["\']csrfmiddlewaretoken["\'][^>]*value=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
        if not match:
            match = re.search(r'value=["\']csrfmiddlewaretoken["\'][^>]*value=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
        
        csrf_token = match.group(1) if match else None
    except:
        csrf_token = None
    
    # Try alternative pattern
    if not csrf_token:
        match = re.search(r'csrfmiddlewaretoken["\']?\s*value=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
        csrf_token = match.group(1) if match else None
    
    if not csrf_token:
        print("    ERROR: CSRF token not found in form!")
        return False
    
    print(f"    ✓ CSRF Token extracted: {csrf_token[:20]}...")
    
    # Step 2: POST login with credentials
    print("\n[2] POST /login/ with credentials (admin / admin123)...")
    
    login_data = {
        'username': 'admin',
        'password': 'admin123',
        'csrfmiddlewaretoken': csrf_token
    }
    
    try:
        response = session.post(
            f"{BASE_URL}/login/",
            data=login_data,
            allow_redirects=False
        )
        print(f"    Status: {response.status_code}")
        
        if response.status_code == 302:
            location = response.headers.get('Location', '')
            print(f"    ✓ Redirect to: {location}")
            
            if 'dashboard' in location:
                print("    ✓ Redirect to dashboard confirmed!")
            else:
                print(f"    WARNING: Unexpected redirect location: {location}")
                
        elif response.status_code == 200:
            print("    Response returned to login page (no redirect)")
            # Check if there's an error message
            if 'error' in response.text.lower() or 'inválido' in response.text.lower():
                print("    ⚠ Error message displayed in response")
                return False
            else:
                print("    WARNING: Login form returned without redirect or error")
                return False
        else:
            print(f"    ERROR: Unexpected status code {response.status_code}")
            return False
            
    except Exception as e:
        print(f"    ERROR: {e}")
        return False
    
    # Step 3: GET dashboard to verify session
    print("\n[3] GET /dashboard/ to verify authentication...")
    try:
        response = session.get(f"{BASE_URL}/dashboard/")
        print(f"    Status: {response.status_code}")
        
        if response.status_code == 200:
            print("    ✓ Dashboard accessible (authenticated)")
            if 'dashboard' in response.text.lower() or 'vehículos' in response.text.lower():
                print("    ✓ Dashboard content loaded successfully")
            return True
        elif response.status_code == 302:
            # Redirect might mean not authenticated
            location = response.headers.get('Location', '')
            print(f"    WARNING: Redirect to {location} (may indicate invalid session)")
            return False
        else:
            print(f"    ERROR: Unexpected status code {response.status_code}")
            return False
            
    except Exception as e:
        print(f"    ERROR: {e}")
        return False

def test_invalid_credentials():
    """Test with invalid credentials"""
    print("\n" + "=" * 60)
    print("Testing with Invalid Credentials")
    print("=" * 60)
    
    session = requests.Session()
    
    # GET login page
    print("\n[1] GET /login/...")
    response = session.get(f"{BASE_URL}/login/")
    
    # Extract CSRF token using regex
    match = re.search(r'csrfmiddlewaretoken["\']?\s*value=["\']([^"\']+)["\']', response.text, re.IGNORECASE)
    csrf_token = match.group(1) if match else None
    
    if not csrf_token:
        print("ERROR: CSRF token not found!")
        return
    
    # POST with invalid credentials
    print("\n[2] POST /login/ with invalid credentials...")
    login_data = {
        'username': 'admin',
        'password': 'wrongpassword',
        'csrfmiddlewaretoken': csrf_token
    }
    
    response = session.post(
        f"{BASE_URL}/login/",
        data=login_data,
        allow_redirects=False
    )
    
    print(f"    Status: {response.status_code}")
    
    if response.status_code == 200:
        print("    ✓ Form re-displayed (not redirected)")
        
        # Check for error message
        if 'Usuario o contraseña inválidos' in response.text:
            print("    ✓ Error message displayed correctly")
        elif 'error' in response.text.lower():
            print("    ✓ Error message present in response")
        else:
            print("    WARNING: No error message found in response")
    else:
        print(f"    WARNING: Status code {response.status_code} (expected 200)")

if __name__ == "__main__":
    print("\nStarting Django Login Tests...")
    print(f"Testing against: {BASE_URL}\n")
    
    try:
        # Test valid credentials
        success = test_login_flow()
        
        # Test invalid credentials
        test_invalid_credentials()
        
        print("\n" + "=" * 60)
        if success:
            print("✓ LOGIN TESTS PASSED")
        else:
            print("✗ LOGIN TESTS FAILED")
        print("=" * 60 + "\n")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
