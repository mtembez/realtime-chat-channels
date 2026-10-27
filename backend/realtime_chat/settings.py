"""Django settings for Real-Time Chat & Channels System."""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps directory to Python path
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "apps"))

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "dev-secret-key-32-chars-minimum-length-realtime-chat"
)

DEBUG = os.environ.get("DEBUG", "1") == "1"

ALLOWED_HOSTS = ["*"]

# Application definition
INSTALLED_APPS = [
    "daphne",  # Must be before django.contrib.staticfiles for ASGI handling
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "channels",
    # Local Apps
    "apps.accounts",
    "apps.chat",
    "apps.notifications",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "realtime_chat.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "realtime_chat.wsgi.application"
ASGI_APPLICATION = "realtime_chat.asgi.application"

# Database configuration (PostgreSQL)
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://jifunze:jifunze@localhost:5432/realtime_chat"
)

if DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://"):
    url = urlparse(DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": url.path[1:],
            "USER": url.username,
            "PASSWORD": url.password,
            "HOST": url.hostname,
            "PORT": url.port or 5432,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Redis Channel Layer for horizontal pub/sub scaling
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS configuration
CORS_ALLOW_ALL_ORIGINS = True

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "send-unread-message-digests-every-5-minutes": {
        "task": "apps.notifications.tasks.send_unread_message_digests",
        "schedule": 300.0,  # Run every 5 minutes
    },
}


# Email Configuration
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.locmem.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@realtimechat.com")

# JWT Security
JWT_SECRET_KEY = SECRET_KEY
JWT_ALGORITHM = "HS256"
JWT_ACCESS_EXPIRATION_MINUTES = 60
JWT_REFRESH_EXPIRATION_DAYS = 30
