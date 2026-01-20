from pathlib import Path
from decouple import config
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
}
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# In a real project, manage this securely (e.g., with environment variables).
SECRET_KEY = 'django-insecure-placeholder-for-development'


DJANGO_APPS = [
    # Django Built-in Apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [

    # Third-Party Apps
    'rest_framework',
    'drf_spectacular',
    'rest_framework_simplejwt',
]

LOCAL_APPS = [
    # Your Local Apps (from the 'apps' folder)
    'apps.core',
    'apps.profiler',
    'apps.users',
    'apps.authentication',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Register your custom implicit signal middleware here
    'apps.core.middleware.ImplicitSignalMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'apps.core.exceptions.global_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'profile_engine.wsgi.application'

DATABASES = {
    'default': { 'ENGINE': 'django.db.backends.postgresql',
                 'NAME': config('DB_NAME', default='profile_engine'), 
                 'USER': config('DB_USER', default='profile_engine_user'), 
                 'PASSWORD': config('DB_PASSWORD', default='SecurePassword123!'), 
                 'HOST': config('DB_HOST', default='localhost'), 
                 'PORT': config('DB_PORT', default='5432'), 
                 'OPTIONS': { 'connect_timeout': 60, }, 
                 'CONN_MAX_AGE': 600, 
                 'CONN_HEALTH_CHECKS': True,
                   }
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Universal Profile Engine API',
    'DESCRIPTION': 'AI-driven domain-agnostic profiling system using Llama 3.2',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

ROOT_URLCONF = 'profile_engine.urls'
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'
