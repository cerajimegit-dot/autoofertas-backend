#!/usr/bin/env python
"""
Script de prueba automática de API endpoints
"""
import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001/api"

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name, passed, message=""):
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"  {status} | {name}")
    if message and not passed:
        print(f"       {Colors.RED}Error: {message}{Colors.END}")

def print_section(title):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Colors.END}")

class APITester:
    def __init__(self):
        self.token = None
        self.refresh_token = None
        self.enterprise_id = None
        self.branch_id = None
        self.brand_id = None
        self.model_id = None
        self.vehicle_id = None
        self.customer_id = None
        self.sale_id = None
        self.quota_id = None
        
    def test_login(self):
        """Prueba de autenticación"""
        print_section("AUTHENTICATION TESTS")
        
        response = requests.post(f"{BASE_URL}/users/login/", json={
            "username": "admin",
            "password": "admin123"
        })
        
        passed = response.status_code == 200
        print_test("Login", passed, response.text if not passed else "")
        
        if passed:
            data = response.json()
            self.token = data.get('access')
            self.refresh_token = data.get('refresh')
            return True
        return False
    
    def get_headers(self):
        """Obtener headers con token"""
        return {"Authorization": f"Bearer {self.token}"}
    
    def test_current_user(self):
        """Prueba obtener usuario actual"""
        response = requests.get(f"{BASE_URL}/users/me/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("Get Current User", passed, response.text if not passed else "")
        return passed
    
    def test_list_branches(self):
        """Prueba listarr sucursales"""
        response = requests.get(f"{BASE_URL}/branches/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("List Branches", passed, response.text if not passed else "")
        
        if passed and response.json():
            self.branch_id = response.json()[0]['id']
        return passed
    
    def test_inventory(self):
        """Pruebas de inventario"""
        print_section("INVENTORY TESTS")
        
        # Crear marca
        response = requests.post(f"{BASE_URL}/brands/", 
            headers=self.get_headers(),
            json={"name": f"TestBrand-{datetime.now().timestamp()}", "is_active": True}
        )
        passed = response.status_code == 201
        print_test("Create Brand", passed, response.text if not passed else "")
        
        if passed:
            self.brand_id = response.json()['id']
        
        # Listar marcas
        response = requests.get(f"{BASE_URL}/brands/", headers=self.get_headers())
        passed = response.status_code == 200 and len(response.json()) > 0
        print_test("List Brands", passed, response.text if not passed else "")
        
        # Crear modelo
        if self.brand_id:
            response = requests.post(f"{BASE_URL}/models/",
                headers=self.get_headers(),
                json={
                    "brand": self.brand_id,
                    "name": f"TestModel-{datetime.now().timestamp()}",
                    "is_active": True
                }
            )
            passed = response.status_code == 201
            print_test("Create Vehicle Model", passed, response.text if not passed else "")
            
            if passed:
                self.model_id = response.json()['id']
        
        # Listar modelos
        response = requests.get(f"{BASE_URL}/models/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("List Vehicle Models", passed, response.text if not passed else "")
        
        # Cotización USD/PYG
        response = requests.post(f"{BASE_URL}/exchange-rates/",
            headers=self.get_headers(),
            json={
                "date": datetime.now().date().isoformat(),
                "usd_to_pyg": 7250.50,
                "is_active": True
            }
        )
        passed = response.status_code == 201
        print_test("Create Exchange Rate", passed, response.text if not passed else "")
        
        # Obtener cotización actual
        response = requests.get(f"{BASE_URL}/exchange-rates/current/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("Get Current Exchange Rate", passed, response.text if not passed else "")
        
        # Crear vehículo
        if self.brand_id and self.model_id and self.branch_id:
            response = requests.post(f"{BASE_URL}/vehicles/",
                headers=self.get_headers(),
                json={
                    "brand": self.brand_id,
                    "model": self.model_id,
                    "year": 2024,
                    "vin": f"TEST{datetime.now().timestamp()}",
                    "license_plate": f"ABC{int(datetime.now().timestamp()) % 1000}",
                    "color": "Blanco",
                    "fob": 15000.00,
                    "container": 200.00,
                    "dispatch": 150.00,
                    "cam_vol": 50.00,
                    "price_currency": "USD",
                    "price": 20000.00,
                    "branch": self.branch_id
                }
            )
            passed = response.status_code == 201
            print_test("Create Vehicle", passed, response.text if not passed else "")
            
            if passed:
                self.vehicle_id = response.json()['id']
        
        # Vehículos disponibles
        response = requests.get(f"{BASE_URL}/vehicles/available/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("List Available Vehicles", passed, response.text if not passed else "")
        
        # Stock valorizado
        response = requests.get(f"{BASE_URL}/vehicles/valorized_stock/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("Get Valorized Stock", passed, response.text if not passed else "")
    
    def test_sales(self):
        """Pruebas de ventas"""
        print_section("SALES TESTS")
        
        # Crear cliente
        response = requests.post(f"{BASE_URL}/customers/",
            headers=self.get_headers(),
            json={
                "name": f"TestCustomer-{datetime.now().timestamp()}",
                "document_type": "CI",
                "document_number": f"{int(datetime.now().timestamp()) % 9999999}",
                "email": f"test{datetime.now().timestamp()}@example.com",
                "phone": "0973123456",
                "address": "Calle Principal 123",
                "city": "Asunción"
            }
        )
        passed = response.status_code == 201
        print_test("Create Customer", passed, response.text if not passed else "")
        
        if passed:
            self.customer_id = response.json()['id']
        
        # Listar clientes
        response = requests.get(f"{BASE_URL}/customers/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("List Customers", passed, response.text if not passed else "")
        
        # Crear forma de pago
        response = requests.post(f"{BASE_URL}/payment-forms/",
            headers=self.get_headers(),
            json={"name": f"Test-{datetime.now().timestamp()}", "is_active": True}
        )
        passed = response.status_code == 201
        print_test("Create Payment Form", passed, response.text if not passed else "")
        
        payment_form_id = response.json()['id'] if passed else None
        
        # Crear venta
        if self.customer_id and self.vehicle_id and payment_form_id:
            response = requests.post(f"{BASE_URL}/sales/",
                headers=self.get_headers(),
                json={
                    "customer": self.customer_id,
                    "vehicle": self.vehicle_id,
                    "unit_price": 20000.00,
                    "discount": 0.00,
                    "payment_form": payment_form_id,
                    "notes": f"Venta de prueba {datetime.now()}"
                }
            )
            passed = response.status_code == 201
            print_test("Create Sale", passed, response.text if not passed else "")
            
            if passed:
                self.sale_id = response.json()['id']
        
        # Listar ventas
        response = requests.get(f"{BASE_URL}/sales/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("List Sales", passed, response.text if not passed else "")
        
        # Ventas del mes
        response = requests.get(f"{BASE_URL}/sales/monthly_sales/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("Get Monthly Sales", passed, response.text if not passed else "")
    
    def test_quotas(self):
        """Pruebas de cuotas"""
        print_section("QUOTAS TESTS")
        
        if not self.sale_id:
            print_test("Create Quota", False, "Sale not created")
            return
        
        # Crear cuota
        due_date = datetime.now() + timedelta(days=30)
        response = requests.post(f"{BASE_URL}/quotas/",
            headers=self.get_headers(),
            json={
                "sale": self.sale_id,
                "plan_name": "Cuota 1/12",
                "total_plan": 12,
                "amount": 1666.67,
                "interest": 0.00,
                "due_date": due_date.date().isoformat(),
                "status": "pending"
            }
        )
        passed = response.status_code == 201
        print_test("Create Quota", passed, response.text if not passed else "")
        
        if passed:
            self.quota_id = response.json()['id']
        
        # Listar cuotas
        response = requests.get(f"{BASE_URL}/quotas/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("List Quotas", passed, response.text if not passed else "")
        
        # Cuotas pendientes
        response = requests.get(f"{BASE_URL}/quotas/pending/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("Get Pending Quotas", passed, response.text if not passed else "")
        
        # Próximos 30 días
        response = requests.get(f"{BASE_URL}/quotas/next_30_days/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("Get Next 30 Days Quotas", passed, response.text if not passed else "")
        
        # Reporte de cuotas
        response = requests.get(f"{BASE_URL}/quotas/quota_report/", headers=self.get_headers())
        passed = response.status_code == 200
        print_test("Get Quota Report", passed, response.text if not passed else "")
        
        # Marcar como pagada
        if self.quota_id:
            response = requests.post(f"{BASE_URL}/quotas/{self.quota_id}/mark_as_paid/",
                headers=self.get_headers()
            )
            passed = response.status_code == 200
            print_test("Mark Quota as Paid", passed, response.text if not passed else "")
            
            # Generar link WhatsApp
            response = requests.get(f"{BASE_URL}/quotas/{self.quota_id}/contact_whatsapp/",
                headers=self.get_headers()
            )
            passed = response.status_code == 200
            print_test("Generate WhatsApp Link", passed, response.text if not passed else "")
    
    def test_dashboard(self):
        """Pruebas de dashboard"""
        print_section("DASHBOARD TESTS")
        
        endpoints = [
            ("summary", "Get Summary"),
            ("sales_by_month", "Get Sales by Month"),
            ("sales_by_branch", "Get Sales by Branch"),
            ("vehicle_models_ranking", "Get Vehicle Models Ranking"),
            ("quotas_status", "Get Quotas Status"),
            ("inventory_stats", "Get Inventory Stats"),
            ("top_customers", "Get Top Customers"),
        ]
        
        for endpoint, name in endpoints:
            response = requests.get(f"{BASE_URL}/dashboard/{endpoint}/", headers=self.get_headers())
            passed = response.status_code == 200
            print_test(name, passed, response.text if not passed else "")
    
    def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        print(f"\n{Colors.BLUE}{'='*60}")
        print("  API SYSTEM TEST SUITE")
        print(f"{'='*60}{Colors.END}")
        
        if not self.test_login():
            print(f"\n{Colors.RED}Cannot proceed without authentication{Colors.END}")
            return
        
        self.test_current_user()
        self.test_list_branches()
        self.test_inventory()
        self.test_sales()
        self.test_quotas()
        self.test_dashboard()
        
        print(f"\n{Colors.BLUE}{'='*60}")
        print("  TEST SUITE COMPLETED")
        print(f"{'='*60}{Colors.END}\n")

if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()
