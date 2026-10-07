"""
Django settings for the Clada Safari Bliss API.

Every deploy-specific value comes from the environment (see .env.example).
Defaults are chosen so `python manage.py runserver` works on a fresh checkout
against SQLite; production is expected to set DATABASE_URL to PostgreSQL.
"""
from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    return default if value in (None, '') else value


def env_bool(name: str, default: bool = False) -> bool:
    return str(env(name, str(default))).lower() in ('1', 'true', 'yes', 'on')


def env_list(name: str, default: str = '') -> list[str]:
    return [item.strip() for item in (env(name, default) or '').split(',') if item.strip()]


DEBUG = env_bool('DJANGO_DEBUG', False)
IS_PRODUCTION = not DEBUG

SECRET_KEY = env('DJANGO_SECRET_KEY', 'dev-only-insecure-secret-key-change-me')
if IS_PRODUCTION and SECRET_KEY.startswith('dev-only'):
    raise RuntimeError('DJANGO_SECRET_KEY is still the development placeholder. Set a real secret.')

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
# Railway sets these at runtime: the generated public domain, and the host its
# health check sends.
if env('RAILWAY_PUBLIC_DOMAIN'):
    ALLOWED_HOSTS += [env('RAILWAY_PUBLIC_DOMAIN'), 'healthcheck.railway.app']

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'django_countries',
    'apps.common',
    'apps.media',
    'apps.accounts',
    'apps.catalog',
    'apps.content',
    'apps.enquiries',
    'apps.seed',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Cookie-authenticated API writes must come from the web app's origin.
    'apps.common.middleware.VerifyOriginMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASES = {
    'default': dj_database_url.parse(
        env('DATABASE_URL', f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
        conn_max_age=int(env('DATABASE_CONN_MAX_AGE', '60')),
        conn_health_checks=True,
    )
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = 'accounts.AdminUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    # Twelve rather than Django's default eight: these accounts publish to the
    # public site and read every customer enquiry, with no second factor.
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

JWT_SECRET = env('JWT_SECRET', SECRET_KEY)
if IS_PRODUCTION and JWT_SECRET.startswith('dev-only'):
    raise RuntimeError('JWT_SECRET is still the development placeholder. Set a real secret.')
JWT_EXPIRES_DAYS = int(env('JWT_EXPIRES_DAYS', '7'))
AUTH_COOKIE_NAME = 'csb_admin_token'
# Scoped to the registrable parent domain in production (e.g. .cladasafaribliss.com)
# so the Next.js server can read the cookie the API sets. Host-only in development.
AUTH_COOKIE_DOMAIN = env('COOKIE_DOMAIN')

# ---------------------------------------------------------------------------
# Web app integration
# ---------------------------------------------------------------------------

# The Next.js origin(s). Used for CORS and for the Origin check on writes.
WEB_ORIGINS = env_list('WEB_ORIGIN', 'http://localhost:3001')
WEB_ORIGIN = WEB_ORIGINS[0]

CORS_ALLOWED_ORIGINS = WEB_ORIGINS
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = WEB_ORIGINS

# Shared secret for the "content changed" webhook to Next.js (/api/revalidate).
REVALIDATE_SECRET = env('REVALIDATE_SECRET', '')
# Where that webhook is sent. Defaults to the public web origin; in Docker set
# it to the web container's internal address, e.g. http://web:3000/api/revalidate.
REVALIDATE_URL = env('REVALIDATE_URL', f'{WEB_ORIGIN}/api/revalidate')

# This service's public origin, baked into uploaded-image URLs.
_railway_url = f'https://{env("RAILWAY_PUBLIC_DOMAIN")}' if env('RAILWAY_PUBLIC_DOMAIN') else None
PUBLIC_API_URL = (env('PUBLIC_API_URL', _railway_url or 'http://localhost:8001') or '').rstrip('/')

# ---------------------------------------------------------------------------
# REST framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'UNAUTHENTICATED_USER': None,
    'EXCEPTION_HANDLER': 'apps.common.exceptions.api_exception_handler',
    'DEFAULT_THROTTLE_RATES': {
        'enquiries': env('THROTTLE_ENQUIRIES', '20/hour'),
    },
    'COERCE_DECIMAL_TO_STRING': False,
}

# Login brute-force guard: failed attempts per client IP per window.
LOGIN_MAX_FAILURES = int(env('LOGIN_MAX_FAILURES', '10'))
LOGIN_FAILURE_WINDOW_SECONDS = 15 * 60

# Throttling counters live in the cache. The local-memory default is per
# process; with several gunicorn workers set CACHE_URL to Redis so the limits
# are shared.
CACHES = {
    'default': (
        {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': env('CACHE_URL')}
        if env('CACHE_URL')
        else {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
    )
}

# ---------------------------------------------------------------------------
# Static and media
# ---------------------------------------------------------------------------

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Whitenoise warns on every request when the directory is missing (before the
# first collectstatic), which buries real warnings in development.
STATIC_ROOT.mkdir(exist_ok=True)
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

MEDIA_URL = '/uploads/'
MEDIA_ROOT = Path(env('MEDIA_ROOT', str(BASE_DIR / 'uploads')))
# Django serves uploads itself unless a reverse proxy takes over /uploads/.
SERVE_MEDIA = env_bool('SERVE_MEDIA', True)
UPLOAD_MAX_BYTES = 6 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 7 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 7 * 1024 * 1024

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_SECURE = IS_PRODUCTION
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
if IS_PRODUCTION:
    SECURE_HSTS_SECONDS = int(env('SECURE_HSTS_SECONDS', '0'))

# ---------------------------------------------------------------------------
# Locale
# ---------------------------------------------------------------------------

LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': env('LOG_LEVEL', 'INFO')},
    'loggers': {
        'django.db.backends': {'level': 'WARNING'},
    },
}
