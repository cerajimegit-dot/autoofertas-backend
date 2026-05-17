"""Dumpea cada modelo por separado para encontrar cual falla."""
import os, sys, subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
os.chdir(BASE_DIR)

# Listado de modelos a probar
MODELS = [
    "core.enterprise",
    "core.branch",
    "core.brand",
    "core.vehiclemodel",
    "core.exchangerate",
    "core.paymentform",
    "core.customuser",
    "core.customuser_branches_visible",
    "core.customuser_groups",
    "core.customuser_user_permissions",
    "core.viewpermission",
    "core.customer",
    "core.vehicle",
    "core.vehiclecost",
    "core.sale",
    "core.quotum",
    "core.auditlog",
    "auth.group",
    "auth.group_permissions",
]

env = os.environ.copy()
env["DB_ENGINE"] = "sqlite"

failed = []
ok = []
for m in MODELS:
    out = f"/tmp/dump_test_{m.replace('.','_')}.json" if os.name != "nt" else f"dump_test_{m.replace('.','_')}.json"
    try:
        result = subprocess.run(
            f'python manage.py dumpdata {m} --indent 0 -o "{out}"',
            shell=True, env=env, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"FAIL  {m}")
            print(f"  stderr: {result.stderr.strip()[:300]}")
            failed.append(m)
        else:
            size = os.path.getsize(out) if os.path.exists(out) else 0
            print(f"OK    {m}  ({size} bytes)")
            ok.append(m)
            try:
                os.remove(out)
            except Exception:
                pass
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT  {m}")
        failed.append(m)

print()
print("=" * 50)
print(f"OK:     {len(ok)}")
print(f"FAILED: {len(failed)}")
for m in failed:
    print(f"  - {m}")
