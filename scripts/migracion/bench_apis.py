"""
Benchmark de endpoints del backend con progreso en vivo.

Uso:
    python scripts\\migracion\\bench_apis.py                 # 5 runs por endpoint
    python scripts\\migracion\\bench_apis.py --runs 3
    python scripts\\migracion\\bench_apis.py --timeout 10    # corta requests >10s
    python scripts\\migracion\\bench_apis.py --tag baseline
"""
import argparse
import csv
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
HISTORY_FILE = BASE_DIR / 'bench_history.csv'


def req(method, url, data=None, token=None, timeout=30):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            payload = resp.read()
            dt = (time.perf_counter() - t0) * 1000
            server_ms = resp.headers.get('X-Response-Time-ms')
            return {
                'status': resp.status,
                'total_ms': dt,
                'server_ms': int(server_ms) if server_ms else None,
                'bytes': len(payload),
                'payload': payload,
            }
    except urllib.error.HTTPError as e:
        dt = (time.perf_counter() - t0) * 1000
        return {'status': e.code, 'total_ms': dt, 'server_ms': None, 'bytes': 0, 'error': f'HTTP {e.code}'}
    except Exception as e:
        dt = (time.perf_counter() - t0) * 1000
        return {'status': None, 'total_ms': dt, 'server_ms': None, 'bytes': 0, 'error': str(e)[:80]}


def stats(values):
    if not values:
        return {'n': 0}
    values = sorted(values)
    n = len(values)
    return {
        'n': n,
        'min': values[0],
        'median': statistics.median(values),
        'mean': statistics.mean(values),
        'p95': values[min(int(n * 0.95), n - 1)],
        'max': values[-1],
    }


ENDPOINTS = [
    ("GET", "/users/me/"),
    ("GET", "/vehicles/?page_size=10"),
    ("GET", "/vehicles/?page_size=50"),
    ("GET", "/vehicles/available/"),
    ("GET", "/brands/"),
    ("GET", "/vehicle-models/"),
    ("GET", "/customers/?page_size=10"),
    ("GET", "/sales/?page_size=10"),
    ("GET", "/sales/?page_size=50"),
    ("GET", "/quotas/?page_size=10"),
    ("GET", "/quotas/pending/"),
    ("GET", "/quotas/overdue/"),
    ("GET", "/payment-forms/"),
    ("GET", "/dashboard/summary/"),
    ("GET", "/dashboard/sales_by_month/"),
    ("GET", "/dashboard/sales_by_branch/"),
    ("GET", "/dashboard/quotas_status/"),
    ("GET", "/dashboard/inventory_stats/"),
    ("GET", "/dashboard/top_customers/"),
    ("GET", "/dashboard/top_morosos/"),
    ("GET", "/dashboard/aging_cuotas/"),
    ("GET", "/dashboard/vehicle_models_ranking/"),
    ("GET", "/dashboard/alertas/"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://localhost:8001/api')
    ap.add_argument('--runs', type=int, default=5)
    ap.add_argument('--timeout', type=int, default=30, help='Timeout por request en segundos')
    ap.add_argument('--username', default='admin')
    ap.add_argument('--password', default='admin123')
    ap.add_argument('--tag', default='')
    ap.add_argument('--warmup', action='store_true', help='Una llamada de warmup que no cuenta')
    args = ap.parse_args()

    base = args.url.rstrip('/')
    print(f"Backend: {base}")
    print(f"Runs por endpoint: {args.runs}  |  Timeout: {args.timeout}s  |  Tag: {args.tag or '-'}")
    print()

    # Login
    print(">>> Login...", end='', flush=True)
    r = req("POST", f"{base}/users/login/",
            data={"username": args.username, "password": args.password},
            timeout=args.timeout)
    if r['status'] != 200:
        print(f"  FAIL: {r.get('error', r.get('status'))}")
        sys.exit(1)
    try:
        token = json.loads(r['payload'])['access']
    except Exception:
        print("  FAIL: respuesta sin 'access' token")
        sys.exit(1)
    print(f" OK ({r['total_ms']:.0f}ms)")

    if args.warmup:
        print(">>> Warmup (no cuenta)...", end='', flush=True)
        for method, path in ENDPOINTS:
            req(method, base + path, token=token, timeout=args.timeout)
        print(" done")

    print()
    print(f">>> Bench {len(ENDPOINTS)} endpoints x {args.runs} runs")
    print(f"{'#':>3} {'endpoint':<45} {'median':>9} {'p95':>9} {'srv':>7}  bytes  notes")
    print("-" * 100)

    results = {}
    try:
        for i, (method, path) in enumerate(ENDPOINTS, 1):
            label = f"{method} {path}"
            url = base + path
            sys.stdout.write(f"{i:>3} {label:<45} ")
            sys.stdout.flush()

            total_times = []
            server_times = []
            errors = 0
            bytes_first = None

            for run in range(args.runs):
                r = req(method, url, token=token, timeout=args.timeout)
                if r['status'] and 200 <= r['status'] < 300:
                    total_times.append(r['total_ms'])
                    if r.get('server_ms') is not None:
                        server_times.append(r['server_ms'])
                    if bytes_first is None:
                        bytes_first = r['bytes']
                else:
                    errors += 1
                # progreso por run
                if total_times:
                    sys.stdout.write(f"{r['total_ms']:.0f}ms ")
                else:
                    sys.stdout.write(f"FAIL ")
                sys.stdout.flush()

            s = stats(total_times)
            sv = stats(server_times)
            results[label] = {'total': s, 'server': sv, 'errors': errors, 'bytes': bytes_first or 0}

            if s['n'] == 0:
                print(f"  -- all failed ({errors})")
            else:
                srv_str = f"{int(sv['median'])}ms" if sv['n'] else '-'
                note = f"err={errors}" if errors else ""
                print(f" => {s['median']:>6.0f}ms  p95 {s['p95']:>5.0f}ms  srv {srv_str:>5}  {bytes_first or 0}b  {note}")
    except KeyboardInterrupt:
        print("\n\n>>> Interrumpido. Mostrando lo que tengo.")

    # Reporte ordenado
    print()
    print("=" * 100)
    print(f"{'Endpoint':<50} {'median':>8} {'p95':>8} {'min':>8} {'max':>8} {'server':>8} {'bytes':>8} {'err':>4}")
    print("-" * 100)
    rows = sorted(
        [(name, r) for name, r in results.items()],
        key=lambda kv: kv[1]['total'].get('median', 0) if kv[1]['total']['n'] else 0,
        reverse=True,
    )
    for name, r in rows:
        s = r['total']
        sv = r['server']
        if s['n'] == 0:
            print(f"{name:<50}  ALL FAILED ({r['errors']} errors)")
            continue
        print(
            f"{name:<50} "
            f"{s['median']:>7.0f}ms {s['p95']:>7.0f}ms {s['min']:>7.0f}ms {s['max']:>7.0f}ms "
            f"{(int(sv['median']) if sv['n'] else 0):>6}ms "
            f"{r['bytes']:>8} {r['errors']:>4}"
        )

    all_medians = [r['total']['median'] for r in results.values() if r['total']['n']]
    if all_medians:
        print()
        print(f"Global median={statistics.median(all_medians):.0f}ms  "
              f"max={max(all_medians):.0f}ms  "
              f"endpoints OK={len(all_medians)}/{len(ENDPOINTS)}")

    # CSV histórico
    write_header = not HISTORY_FILE.exists()
    with open(HISTORY_FILE, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(['timestamp', 'tag', 'endpoint', 'runs', 'median_ms', 'p95_ms', 'min_ms', 'max_ms', 'bytes', 'errors'])
        ts = datetime.now().isoformat(timespec='seconds')
        for name, r in results.items():
            s = r['total']
            if s['n'] == 0:
                continue
            w.writerow([ts, args.tag, name, s['n'], f"{s['median']:.0f}", f"{s['p95']:.0f}",
                        f"{s['min']:.0f}", f"{s['max']:.0f}", r['bytes'], r['errors']])
    print(f"\nHistórico actualizado en {HISTORY_FILE}")


if __name__ == '__main__':
    main()
