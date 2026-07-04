"""Verifica que la barrera JR_MODE esta activa y funciona.

Corrida contra la rama jr/onboarding: DEBE bloquear DB_ENGINE=postgres.
Si NO bloquea, el Jr esta en peligro. Escalar al senior.

USO:
    python scripts/verify_jr_safety.py
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    marker = root / '.jr_mode'
    print()
    print('=' * 70)
    print('  VERIFICACION DE BARRERAS JR_MODE')
    print('=' * 70)
    print()

    ok = True

    # Test 1: existe .jr_mode
    print('[1/3] Verificando que existe el archivo .jr_mode ...')
    if marker.exists():
        print('      OK ✓ existe')
    else:
        print('      FALLO ✗ no existe — la barrera 2 esta desactivada!')
        ok = False

    # Test 2: settings.py tiene la barrera
    print('[2/3] Verificando que settings.py tiene el chequeo ...')
    settings_content = (root / 'playas_autos' / 'settings.py').read_text(encoding='utf-8')
    if 'JR_MODE_MARKER' in settings_content and 'JR_MODE activo' in settings_content:
        print('      OK ✓ el codigo tiene la barrera')
    else:
        print('      FALLO ✗ falta la barrera en settings.py!')
        ok = False

    # Test 3: al setear DB_ENGINE=postgres, Django rechaza
    print('[3/3] Probando que DB_ENGINE=postgres se bloquea de verdad ...')
    env = os.environ.copy()
    env['DB_ENGINE'] = 'postgres'
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    result = subprocess.run(
        [sys.executable, 'manage.py', 'check'],
        cwd=root, env=env, capture_output=True, text=True,
    )
    if result.returncode != 0 and 'JR_MODE activo' in (result.stderr + result.stdout):
        print('      OK ✓ Django rechaza con mensaje claro')
    else:
        print('      FALLO ✗ Django NO rechazo — la barrera esta rota!')
        print('      stdout:', result.stdout[:200])
        print('      stderr:', result.stderr[:200])
        ok = False

    print()
    if ok:
        print('=' * 70)
        print('  TODAS LAS BARRERAS ESTAN ACTIVAS ✓')
        print('  Podes trabajar tranquilo — no vas a tocar produccion por error.')
        print('=' * 70)
        sys.exit(0)
    else:
        print('=' * 70)
        print('  ALGUNA BARRERA FALLO ✗')
        print('  Avisale al senior INMEDIATAMENTE antes de correr algo.')
        print('=' * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
