import os
from pathlib import Path
from config.settings import Settings
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

settings = Settings()

SECRET_KEY = settings.DJANGO_SECRET_KEY

DEBUG = settings.DEBUG

ALLOWED_HOSTS = [host.strip() for host in settings.ALLOWED_HOSTS.split(",") if host.strip()]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
] + [origin.strip() for origin in settings.CORS_EXTRA_ORIGINS.split(",") if origin.strip()]

# apiFetch sends credentials, so the browser requires the exact origin echoed back.
CORS_ALLOW_CREDENTIALS = True


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'app',
    'api',
    "corsheaders",
    "ninja_extra",
    "ninja_jwt",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "app.wsgi.application"


if settings.DATABASE_URL:
    # Imported here so the compose path below needs no extra dependency installed.
    import dj_database_url

    DATABASES = {
        # Neon drops idle connections, so a persistent one is dead on reuse; its
        # pooler makes opening a fresh connection per request cheap.
        "default": dj_database_url.parse(
            settings.DATABASE_URL, conn_max_age=0, ssl_require=True,
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "backend_db",
            "USER": "admin",
            "PASSWORD": "admin",
            "HOST": "nba_app-postgres-host-1",
            "PORT": "5432",
        }
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",  # Change to INFO, DEBUG, ERROR as needed
    },
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

NINJA_JWT = {
    "SIGNING_KEY": settings.JWT_SIGNING_KEY,
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}