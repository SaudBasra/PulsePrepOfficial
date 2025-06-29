import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local-default-secret-key')

# Automatically toggle debug based on environment
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

# ALLOWED_HOSTS handles both development and production
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'pulseprep.net').split()

# ================================
# APPLICATION DEFINITION
# ================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Your apps
    'main',
    'dashboard',
    'user_management',
    'questionbank',
    'managemodule',
    'mocktest',
    'analytics_report',
    'myaccount',
    'notifications',
    'setting',
    'modelpaper',
    'manageimage',
    'notes',
]

# ================================
# MIDDLEWARE CONFIGURATION
# ================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom middleware (keeping your working setup)
    'user_management.middleware.SingleSessionMiddleware',
    'user_management.middleware.AutomaticAccessControlMiddleware',
    'user_management.middleware.BackButtonSecurityMiddleware',  # NEW: Added from localhost
]

ROOT_URLCONF = 'config.urls'

# ================================
# TEMPLATE CONFIGURATION
# ================================
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
                
                # Custom context processors (organized and deduplicated)
                'user_management.context_processors.admin_navigation_stats',  # NEW: Added from localhost
                'user_management.context_processors.user_stats',  # Existing
                'user_management.context_processors.user_access_context',  # NEW: Added from localhost
                'notifications.context_processors.notification_context',  # Existing
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ================================
# DATABASE CONFIGURATION
# ================================
# Production database (PostgreSQL) - Active configuration
DATABASES = {
    'default': {
       'NAME': 'pulseprep_db',
        'USER': 'pulseprep_user',
        'PASSWORD': 'Ppproject@#12345',
       'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Development database configuration (commented out)
# Uncomment this and comment out the PostgreSQL config above for local development:
#
# Database config (SQLite for now)
#DATABASES = {
 #   'default': {
  #      'ENGINE': 'django.db.backends.sqlite3',
   #     'NAME': BASE_DIR / 'db.sqlite3',
   # }
#}

# ================================
# #STATIC AND MEDIA FILES
# ================================
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']  # Used in development

# Always define STATIC_ROOT for collectstatic to work
STATIC_ROOT = '/opt/PulsePrep/staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'




# ================================
# PASSWORD VALIDATION
# ================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ================================
# INTERNATIONALIZATION
# ================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ================================
# AUTHENTICATION CONFIGURATION
# ================================
AUTH_USER_MODEL = 'user_management.CustomUser'

# Authentication settings
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True

# ================================
# EMAIL CONFIGURATION (ZOHO)
# ================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.zoho.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False  # Important: Don't use both TLS and SSL
EMAIL_HOST_USER = 'support@pulseprep.net'
EMAIL_HOST_PASSWORD = 'Ppproject#123'
DEFAULT_FROM_EMAIL = 'PulsePrep Support <support@pulseprep.net>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Email timeout settings
EMAIL_TIMEOUT = 30

# For debugging email issues in development
if DEBUG:
    # Uncomment this line temporarily to see emails in console during development
    # EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    pass

# ================================
# ACCESS CONTROL CONFIGURATION (NEW)
# ================================
ACCESS_CONTROL = {
    # Whether to log access attempts (set to False for development, True for production monitoring)
    'LOG_ACCESS_ATTEMPTS': not DEBUG,
    
    # Whether to enforce single session per user
    'ENFORCE_SINGLE_SESSION': True,
    
    # Whether admins bypass all restrictions
    'ADMIN_BYPASS_ALL': True,
    
    # Default redirect for access denied
    'ACCESS_DENIED_REDIRECT': '/dashboard/',
}

# ================================
# CONTENT FILTERING CONFIGURATION (NEW)
# ================================
CONTENT_FILTERING = {
    # Strict filtering (students see only their exact degree/year)
    'STRICT_YEAR_FILTERING': True,
    
    # Allow students to see previous years' content
    'ALLOW_PREVIOUS_YEARS': False,
    
    # Allow cross-degree content viewing
    'ALLOW_CROSS_DEGREE': False,
}

# ================================
# DATA UPLOAD CONFIGURATION
# ================================
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100000

# ================================
# LOGGING CONFIGURATION
# ================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'django.log',
            'formatter': 'verbose',
        },
        'email_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'email.log',
            'formatter': 'verbose',
        },
        'notifications_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'notifications.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        # Django email logging
        'django.core.mail': {
            'handlers': ['console', 'email_file'] if DEBUG else ['email_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        # Custom email service logging
        'user_management.email_service': {
            'handlers': ['console', 'email_file'] if DEBUG else ['email_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Notifications logging (existing)
        'notificationsetting': {
            'handlers': ['notifications_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Django root logger
        'django': {
            'handlers': ['console', 'file'] if DEBUG else ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Your app loggers
        'user_management': {
            'handlers': ['console', 'file'] if DEBUG else ['file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'mocktest': {
            'handlers': ['console', 'file'] if DEBUG else ['file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'] if DEBUG else ['file'],
        'level': 'WARNING',
    },
}

# ================================
# SECURITY SETTINGS (PRODUCTION)
# ================================
if not DEBUG:
    # HTTPS settings
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # Security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # Session security
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # HSTS settings (uncomment after ensuring HTTPS works)
    # SECURE_HSTS_SECONDS = 31536000
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_PRELOAD = True

# ================================
# ENVIRONMENT-SPECIFIC OVERRIDES
# ================================
# Allow environment variables to override specific settings
if os.getenv('DJANGO_EMAIL_BACKEND'):
    EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND')

if os.getenv('DJANGO_LOG_LEVEL'):
    for logger in LOGGING['loggers'].values():
        logger['level'] = os.getenv('DJANGO_LOG_LEVEL')

# Development-specific settings
if DEBUG:
    # Additional development tools can be added here
    # Example: django-debug-toolbar
    pass