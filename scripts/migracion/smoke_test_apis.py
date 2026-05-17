"""
Smoke test de las APIs corriendo contra Postgres.
Asume que el server Django esta corriendo en localhost:8001 con DB_ENGINE=postgres.

Uso:
    1. En una terminal: scripts\\run_backend.bat  (o python manage.py runserver 0.0.0.0:8001)
    2. En otra: python scripts\\migracion\\smoke_test_apis.py
"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8001/api"
USERNAME = "admin"   # ajustar si se cambio
PASSWORD = "admin123"

results = []


def req(method, path, data=None, token=None, expect_status=None):
    url = BASE + path
    body = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text) if text else None
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(text)
        except Exception:
            payload = text
        return e.code, payload
    except Exception as e:
        return None, str(e)


def test(name, fn):
    try:
        status, data = fn()
        ok = 200 <= (status or 0) < 300
        results.append((ok, name, status, data if not ok else "..."))
        print(f"  {'OK' if ok else 'FAIL'}  {name:<40}  status={status}")
        if not ok:
            print(f"        -> {data}")
        return data if ok else None
    except Exception as e:
        results.append((False, name, None, str(e)))
        print(f"  CRASH {name}: {e}")
        return None


print("=" * 70)
print("SMOKE TEST APIs - Backend Django sobre Postgres")
print("=" * 70)

# 1. Login
print("\n[1] Auth")
login = test("POST /users/login (admin)", lambda: req("POST", "/users/login/", {"username": USERNAME, "password": PASSWORD}))
if not login or "access" not in (login or {}):
    print("\nNo se pudo loguear. Abortando. Verificar credenciales/usuario admin existe.")
    sys.exit(1)
token = login["access"]
print(f"  Token obtenido (len={len(token)})")

# 2. Endpoints GET de lectura (listados)
print("\n[2] Lecturas")
tests = [
    ("GET /users/me", "/users/me/"),
    ("GET /vehicles?page_size=5", "/vehicles/?page_size=5"),
    ("GET /vehicles/available", "/vehicles/available/"),
    ("GET /brands", "/brands/"),
    ("GET /vehicle-models", "/vehicle-models/"),
    ("GET /customers?page_size=5", "/customers/?page_size=5"),
    ("GET /sales?page_size=5", "/sales/?page_size=5"),
    ("GET /quotas?page_size=5", "/quotas/?page_size=5"),
    ("GET /quotas/pending", "/quotas/pending/"),
    ("GET /quotas/overdue", "/quotas/overdue/"),
    ("GET /payment-forms", "/payment-forms/"),
    ("GET /dashboard/summary", "/dashboard/summary/"),
    ("GET /dashboard/sales_by_month", "/dashboard/sales_by_month/"),
    ("GET /dashboard/sales_by_branch", "/dashboard/sales_by_branch/"),
    ("GET /dashboard/quotas_status", "/dashboard/quotas_status/"),
    ("GET /dashboard/inventory_stats", "/dashboard/inventory_stats/"),
    ("GET /dashboard/top_customers", "/dashboard/top_customers/"),
    ("GET /dashboard/aging_cuotas", "/dashboard/aging_cuotas/"),
    ("GET /dashboard/alertas", "/dashboard/alertas/"),
]
for label, path in tests:
    test(label, lambda p=path: req("GET", p, token=token))

# 3. Verificar conteos coinciden con BD
print("\n[3] Sanity checks de conteos")
status, data = req("GET", "/sales/?page_size=1", token=token)
n_sales = (data or {}).get("count", 0) if isinstance(data, dict) else 0
status, data = req("GET", "/vehicles/?page_size=1", token=token)
n_vehicles = (data or {}).get("count", 0) if isinstance(data, dict) else 0
status, data = req("GET", "/customers/?page_size=1", token=token)
n_customers = (data or {}).get("count", 0) if isinstance(data, dict) else 0
status, data = req("GET", "/quotas/?page_size=1", token=token)
n_quotas = (data or {}).get("count", 0) if isinstance(data, dict) else 0
print(f"  Sales:     {n_sales}")
print(f"  Vehicles:  {n_vehicles}")
print(f"  Customers: {n_customers}")
print(f"  Quotas:    {n_quotas}")

# Resumen
print("\n" + "=" * 70)
ok_count = sum(1 for r in results if r[0])
fail_count = sum(1 for r in results if not r[0])
print(f"RESULTADO: {ok_count} OK / {fail_count} FAIL")
if fail_count:
    print("\nFallidas:")
    for ok, name, status, data in results:
        if not ok:
            print(f"  - {name} (status={status})")
    sys.exit(1)
else:
    print("\nTodas las APIs responden OK")
