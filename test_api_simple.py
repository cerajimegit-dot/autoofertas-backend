#!/usr/bin/env python
"""
Script de prueba simplificado para API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8001/api"

def test_login():
    """Prueba de autenticación"""
    print("\n=== AUTENTICACION ===")
    
    response = requests.post(f"{BASE_URL}/users/login/", json={
        "username": "admin",
        "password": "admin123"
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("LOGIN: OK")
        data = response.json()
        return data.get('access')
    else:
        print(f"LOGIN: ERROR - {response.text[:200]}")
        return None

def test_endpoints(token):
    """Probar endpoints principales"""
    print("\n=== ENDPOINTS ===")
    
    endpoints = [
        ("users/me/", "GET", "Get Current User"),
        ("branches/", "GET", "List Branches"),
        ("brands/", "GET", "List Brands"),
        ("vehicles/", "GET", "List Vehicles"),
        ("customers/", "GET", "List Customers"),
        ("sales/", "GET", "List Sales"),
        ("quotas/", "GET", "List Quotas"),
        ("dashboard/summary/", "GET", "Dashboard Summary"),
    ]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    for endpoint, method, name in endpoints:
        url = f"{BASE_URL}/{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=5)
            status = response.status_code
            symbol = "OK" if status in [200, 201] else "ERROR"
            print(f"  {symbol:5} | {status} | {name}")
        except Exception as e:
            print(f"  ERROR | --- | {name} - {str(e)[:50]}")

if __name__ == "__main__":
    print("Iniciando pruebas de API...")
    print(f"URL Base: {BASE_URL}")
    
    token = test_login()
    if token:
        print("\nToken obtenido exitosamente")
        test_endpoints(token)
        print("\nPruebas completadas!")
    else:
        print("\nNo se pudo obtener token - abortando pruebas")
