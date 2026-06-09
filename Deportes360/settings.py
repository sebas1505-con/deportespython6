from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# ── SEGURIDAD ───────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-hv$y6kuexh^^=b3f%3zn^(f-6r=r0i46&&7u&b5*ufq4$_q$7r'
)
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

_raw_hosts = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip()]
# Subdomain wildcard de Railway — matchea cualquier *.up.railway.app
if not any('railway.app' in h for h in ALLOWED_HOSTS):
    ALLOWED_HOSTS.append('.railway.app')

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
for _h in ALLOWED_HOSTS:
    if _h.startswith('.') or _h in ('localhost', '127.0.0.1', '*'):
        continue
    CSRF_TRUSTED_ORIGINS.extend([f'https://{_h}', f'http://{_h}'])
# Dominio público configurado explícitamente en Railway (variable APP_URL)
_app_url = os.environ.get('APP_URL', '')
if _app_url and _app_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(_app_url)

# ── APPS ────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',
    'usuarios',
    'inventario',
    'rest_framework',
    'corsheaders',
]

# ── MIDDLEWARE ───────────────────────────────────────────────────────────────
# WhiteNoise va justo después de SecurityMiddleware para servir estáticos
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
]

ROOT_URLCONF = 'Deportes360.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'Deportes360.wsgi.application'

# ── BASE DE DATOS ─────────────────────────────────────────────────────────────
# Railway inyecta MYSQLHOST, MYSQLUSER, MYSQLPASSWORD, MYSQLDATABASE, MYSQLPORT
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME':     os.environ.get('MYSQLDATABASE') or os.environ.get('DB_NAME',     '360deportes'),
        'USER':     os.environ.get('MYSQLUSER')     or os.environ.get('DB_USER',     'root'),
        'PASSWORD': os.environ.get('MYSQLPASSWORD') or os.environ.get('DB_PASSWORD', '123456789'),
        'HOST':     os.environ.get('MYSQLHOST')     or os.environ.get('DB_HOST',     'localhost'),
        'PORT':     os.environ.get('MYSQLPORT')     or os.environ.get('DB_PORT',     '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'connect_timeout': 10,
        },
    }
}

# ── VALIDACIÓN DE CONTRASEÑAS ────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── INTERNACIONALIZACIÓN ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-co'
TIME_ZONE     = 'America/Bogota'
USE_I18N      = True
USE_TZ        = False

# ── ARCHIVOS ESTÁTICOS ────────────────────────────────────────────────────────
STATIC_URL   = '/static/'
STATIC_ROOT  = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# WhiteNoise: compresión sin manifest (más estable en Railway)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Servir videos MP4 correctamente
WHITENOISE_MIMETYPES = {
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
    '.ogg': 'video/ogg',
}
# No comprimir videos (ya están comprimidos)
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = [
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'zip', 'gz', 'tgz', 'bz2', 'tbz',
    'xz', 'br', 'swf', 'flv', 'woff', 'woff2', 'mp4', 'webm', 'ogg', 'mp3',
]

# ── ARCHIVOS MEDIA ────────────────────────────────────────────────────────────
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── CLOUDINARY (almacenamiento de imágenes en la nube) ────────────────────────
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY':    os.environ.get('CLOUDINARY_API_KEY',    ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}
# Usar Cloudinary en producción; disco local en desarrollo
if os.environ.get('CLOUDINARY_CLOUD_NAME'):
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# ── AUTH ──────────────────────────────────────────────────────────────────────
LOGIN_URL           = 'login'
LOGIN_REDIRECT_URL  = 'index'
LOGOUT_REDIRECT_URL = 'index'

# ── EMAIL ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = 'smtp.gmail.com'
EMAIL_PORT          = 587
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = os.environ.get('EMAIL_HOST_USER',     'juancerquera104@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'xpni nsdy heqa pfia')
DEFAULT_FROM_EMAIL  = f'Soporte Deportes360 <{EMAIL_HOST_USER}>'

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Solo en desarrollo

# ── LOGGING PRODUCCIÓN ─────────────────────────────────────────────────────────
if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {'class': 'logging.StreamHandler'},
        },
        'root': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'loggers': {
            'django': {
                'handlers': ['console'],
                'level': 'ERROR',
                'propagate': False,
            },
        },
    }
