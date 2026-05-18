"""
Django settings for playas_autos project.
"""

import os
from pathlib import Path
from decouple import config, Csv
from datetime import timedelta

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# El default sólo sirve para desarrollo. En prod la variable de entorno
# SECRET_KEY DEBE estar definida — si no, fallamos rápido más abajo.
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG=True deja accesibles trazas y datos sensibles ante cualquier 500;
# en producción siempre False (DEBUG=False en el .env).
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Detección de entorno productivo: True cuando DEBUG=False y SECRET_KEY no
# es el default inseguro. Lo usamos para forzar HTTPS, cookies seguras, etc.
IS_PRODUCTION = (not DEBUG) and (not SECRET_KEY.startswith('django-insecure-'))

if IS_PRODUCTION and SECRET_KEY.startswith('django-insecure-'):
    # Doble guard: si alguien pone DEBUG=False sin cambiar el SECRET_KEY,
    # fallamos al iniciar Django en lugar de servir con un secret conocido.
    raise RuntimeError(
        'SECRET_KEY no configurada para producción. '
        'Definí la variable de entorno SECRET_KEY antes de bootear.'
    )

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    
    # Local apps
    'core',
    'ui',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.AuditLogMiddleware',
    'core.middleware.TimingMiddleware',
]

ROOT_URLCONF = 'playas_autos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'playas_autos.wsgi.application'

# Database
# DB_ENGINE: "sqlite" (default) o "postgres"
# Para Postgres, definir DATABASE_URL en .env (formato: postgresql://user:pass@host:port/dbname)
DB_ENGINE = config('DB_ENGINE', default='sqlite')

if DB_ENGINE == 'postgres':
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(
            config('DATABASE_URL'),
            # Con transaction pooler (puerto 6543) podemos mantener conexion persistente:
            # cada request reusa la TCP/SSL en vez de hacer handshake nuevo (~2s).
            conn_max_age=600,
            conn_health_checks=True,  # antes de reusar, verifica que sigue viva
            ssl_require=False,
        )
    }
    # Transaction pooler de Supabase no soporta prepared statements:
    # https://supabase.com/docs/guides/database/connecting-to-postgres#shared-pooler
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS'].update({
        # psycopg2 no expone prepare_threshold, pero podemos forzar autocommit-friendly:
        # No hay parametro directo; el server-side cursor causa el problema.
        # Solucion: DISABLE_SERVER_SIDE_CURSORS evita server-side cursors.
    })
    DATABASES['default']['DISABLE_SERVER_SIDE_CURSORS'] = True
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-es'

TIME_ZONE = 'America/Asuncion'

USE_I18N = True

USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# STATICFILES_DIRS solo si la carpeta /static existe (en algunos despliegues no se commitea)
if os.path.isdir(os.path.join(BASE_DIR, 'static')):
    STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
# WhiteNoise: servir static comprimido y con hash en produccion
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'core.CustomUser'

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.DefaultPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    # === Throttling (anti brute-force y anti scraping) ===
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        # Cualquier request anónimo
        'anon': config('THROTTLE_ANON', default='60/min'),
        # Cualquier usuario autenticado
        'user': config('THROTTLE_USER', default='600/min'),
        # Scopes específicos (usados con throttle_scope en acciones puntuales)
        'login':    config('THROTTLE_LOGIN',    default='5/min'),
        'register': config('THROTTLE_REGISTER', default='3/min'),
        'whatsapp': config('THROTTLE_WHATSAPP', default='30/min'),
    },
}

# JWT configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    # Rotamos el refresh token con cada uso y blacklisteamos el anterior.
    # Eso convierte el logout en una operación real (el refresh deja de
    # servir) y limita el daño si un token se roba.
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'ALGORITHM': config('JWT_ALGORITHM', default='HS256'),
    'SIGNING_KEY': config('JWT_SECRET', default=SECRET_KEY),
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JTI_CLAIM': 'jti',
    'TOKEN_TYPE_CLAIM': 'token_type',
    'JTI_CLAIM': 'jti',

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

    'JTI_CLAIM': 'jti',
    'TOKEN_TYPE_CLAIM': 'token_type',

    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

# CORS configuration
# En producción debe contener exclusivamente el o los dominios del frontend
# (ej: https://autoofertas.com.py). Nunca usar `CORS_ALLOW_ALL_ORIGINS=True`.
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=Csv()
)
CORS_ALLOW_CREDENTIALS = True
# En producción exigimos que CORS esté en una whitelist explícita, no
# permisivo a todos los orígenes.
if IS_PRODUCTION:
    CORS_ALLOW_ALL_ORIGINS = False

# ====================================================================
# Hardening de producción
# ====================================================================
# Sólo activamos HTTPS strict, HSTS y cookies seguras cuando estamos en un
# entorno productivo real (DEBUG=False + SECRET_KEY no default). En dev
# local conviene dejarlos apagados.
if IS_PRODUCTION:
    # Render/Heroku/Fly terminan TLS en su proxy y pasan el header
    # X-Forwarded-Proto. Sin esto, Django no detecta que la request es https.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Redirigir cualquier http:// a https://
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)

    # HSTS: forzar al browser a usar https en visitas siguientes.
    # Empezamos con 1 hora; subir a 1 año (31536000) tras 1 semana sin
    # problemas. NO usar includeSubDomains hasta confirmar que TODO está en
    # https (cualquier subdominio sin TLS quedaría inaccesible).
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=3600, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
    SECURE_HSTS_PRELOAD = False

    # Cookies sólo por canal seguro y no accesibles por JS.
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = False  # CSRF se lee desde JS para el header
    CSRF_COOKIE_SAMESITE = 'Lax'

    # Otros headers de seguridad estándar de Django
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

    # El admin de Django sólo via HTTPS — además, si querés esconderlo,
    # cambiá `playas_autos/urls.py:admin/` por algo no-adivinable.

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
    'loggers': {
        'perf': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Swagger/OpenAPI configuration
SPECTACULAR_SETTINGS = {
    'TITLE': 'Sistema de Gestión de Playas de Autos - API',
    'DESCRIPTION': 'API REST para gestión integral de playas de autos con autenticación JWT y soporte multiempresa',
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAuthenticated'],
    'SERVE_AUTHENTICATION': ['rest_framework_simplejwt.authentication.JWTAuthentication'],
}

# Django Forms / Authentication
LOGIN_URL = 'ui:login'
LOGIN_REDIRECT_URL = 'ui:dashboard'
LOGOUT_REDIRECT_URL = 'ui:login'

# ===== EMAIL =====
# Por default usamos el backend de consola (imprime a stdout) — útil para
# desarrollo y para que los management commands se vean en logs de cron.
# En producción, si están seteadas las env vars de SMTP, usamos SMTP real.
EMAIL_HOST = config('EMAIL_HOST', default='')
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL',
                                default=f'AUTO OFERTAS <{EMAIL_HOST_USER}>')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'noreply@autoofertas.local'

# Destinatario default para el digest diario; coma-separado en .env
DAILY_DIGEST_RECIPIENTS = config('DAILY_DIGEST_RECIPIENTS', default='', cast=Csv())

# ===== UMBRALES DE ALERTAS =====
# Configurables vía env vars. Los usa /dashboard/active_alerts/ y el digest.
# Tipos:
#   - *_WARN: amarillo, "ojo".
#   - *_CRIT: rojo, "intervenir ya".
ALERT_THRESHOLDS = {
    'mora_pct_warn':       config('ALERT_MORA_PCT_WARN',       default=10.0, cast=float),
    'mora_pct_crit':       config('ALERT_MORA_PCT_CRIT',       default=25.0, cast=float),
    'estancados_warn':     config('ALERT_ESTANCADOS_WARN',     default=5,    cast=int),
    'estancados_crit':     config('ALERT_ESTANCADOS_CRIT',     default=15,   cast=int),
    'vencidas_count_warn': config('ALERT_VENCIDAS_COUNT_WARN', default=10,   cast=int),
    'vencidas_count_crit': config('ALERT_VENCIDAS_COUNT_CRIT', default=20,   cast=int),
    'dias_pago_warn':      config('ALERT_DIAS_PAGO_WARN',      default=3.0,  cast=float),
    'dias_pago_crit':      config('ALERT_DIAS_PAGO_CRIT',      default=7.0,  cast=float),
}
