"""Settings para correr pytest sin tocar Supabase.

Hereda todo de settings.py pero fuerza:
  - SQLite en memoria (rápido, aislado, no requiere CREATEDB).
  - Cache local (LocMemCache) — sin Redis ni recetas externas.
  - Migraciones aplicadas (no `--keepdb` con Postgres prod).

Uso: `pytest` desde la raíz, gracias a `pytest.ini` que apunta acá.
"""
from .settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# El TimingMiddleware y AuditLogMiddleware no aportan en tests y enlentecen.
MIDDLEWARE = [m for m in MIDDLEWARE if not m.endswith((
    'TimingMiddleware', 'AuditLogMiddleware',
))]

# Acelera el hashing en tests (no perdemos seguridad — son passwords falsas).
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
