"""
Django settings for WheelsOn project.

Red profesional basada en base de datos de grafos (Neo4j).
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==============================================================================
# CORE SETTINGS
# ==============================================================================

# Sin archivo .env la app arranca en modo seguro: sin depuración, y exige una clave propia
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('Define DJANGO_SECRET_KEY: copia wheelson/.env.example a wheelson/.env.')
    SECRET_KEY = 'django-insecure-solo-para-desarrollo-local'

ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

# Modo demo: habilita el acceso rápido y Cambiar perspectiva, útiles para probar y presentar.
WHEELSON_MODO_DEMO = os.getenv('WHEELSON_MODO_DEMO', str(DEBUG)).lower() in ('true', '1', 'yes')

SESSION_COOKIE_SECURE = not DEBUG and os.getenv('WHEELSON_HTTPS', 'False').lower() in ('true', '1', 'yes')
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE


# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'django_htmx',

    # Local apps
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',      # Servir archivos estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',           # Soporte HTMX
    'core.middleware.SesionRequeridaMiddleware',       # Exige sesión y carga al usuario actual
    'core.middleware.Neo4jNoDisponibleMiddleware',     # Error claro si Neo4j no responde
]

ROOT_URLCONF = 'wheelson.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'core' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.social_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'wheelson.wsgi.application'


# ==============================================================================
# DATABASE (SQLite para sesiones Django + Neo4j para datos del grafo)
# ==============================================================================

# SQLite solo para sesiones/auth de Django (mínimo necesario)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Neo4j - Base de datos de grafos (configuración principal)
NEOMODEL_NEO4J_BOLT_URL = os.getenv(
    'NEO4J_BOLT_URL',
    'bolt://neo4j:password@localhost:7687'
)

NEOMODEL_ENCRYPTED = os.getenv('NEO4J_ENCRYPTED', 'False').lower() in ('true', '1')

# Los tests usan su propio Neo4j porque borran todos los datos (ver core/test_utils.py)
TEST_RUNNER = 'core.test_utils.Neo4jTestRunner'


# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = 'es'

TIME_ZONE = 'America/Bogota'

USE_I18N = True

USE_TZ = True


# ==============================================================================
# STATIC FILES (CSS, JavaScript, Images)
# ==============================================================================

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

# Sin manifiesto ni collectstatic: con DEBUG=False (modo presentación) WhiteNoise sirve los
# archivos directo desde static/. Así la app corre igual en cualquier computador del equipo.
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

# Un formulario de una pestaña vieja (por ejemplo, tras cambiar de usuario) vuelve a la página
# con un aviso, en lugar de la página técnica de Django.
CSRF_FAILURE_VIEW = "core.views.csrf_vencido"


# ==============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ==============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ==============================================================================
# WHEELSON CUSTOM SETTINGS
# ==============================================================================

APP_NAME = 'WheelsOn'
ITEMS_PER_PAGE = 12
MAX_RECOMMENDATIONS = 10
