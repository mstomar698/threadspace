"""
Django settings for the ThreadSpace backend.

Configuration is read from the environment (12-factor style) via django-environ.
See .env.example for the supported variables.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only-secret-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "core",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.urls"

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

WSGI_APPLICATION = "backend.wsgi.application"


# Database
# Reads DATABASE_URL when present, otherwise falls back to a local sqlite file.
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}


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


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
# Hashed + compressed static files (needs `collectstatic`). Enable in production.
if env.bool("USE_MANIFEST_STATIC", default=False):
    STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Security hardening. Defaults are safe for local/dev and tests; enable these
# explicitly via the environment in production (see .env.example).
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ThreadSpace API",
    "DESCRIPTION": "A build-in-public social network for the open-source world.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("ACCESS_TOKEN_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("REFRESH_TOKEN_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
}

# CORS (for the future Next.js frontend)
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS", default=["http://localhost:3000", "http://127.0.0.1:3000"]
)

# Key for encrypting secrets at rest (e.g. stored GitHub OAuth tokens). When
# unset, a key is derived from SECRET_KEY. In production, set a dedicated
# Fernet key: `python -c "from cryptography.fernet import Fernet;
# print(Fernet.generate_key().decode())"`.
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")

# Optional GitHub token to raise the public API rate limit for repo enrichment.
GITHUB_API_TOKEN = env("GITHUB_API_TOKEN", default="")

# Test-only: when enabled, the GitHub network helpers return canned data instead
# of calling github.com. Used by the Playwright e2e stack so the real backend
# runs end-to-end without external dependencies. NEVER enable in production.
GITHUB_STUB = env.bool("GITHUB_STUB", default=False)

# GitHub OAuth (sign in with GitHub + "Connect GitHub"). Credentials come from a
# GitHub OAuth App whose callback is <FRONTEND_URL>/github/callback. Use separate
# apps for local and production (each has its own registered callback URL): the
# *_PROD pair is used when DEBUG is off, otherwise the local pair. Either may be
# omitted, which disables the GitHub endpoints. When unset, the endpoints 503.
GITHUB_OAUTH_CLIENT_ID = env("GITHUB_OAUTH_CLIENT_ID", default="")
GITHUB_OAUTH_CLIENT_SECRET = env("GITHUB_OAUTH_CLIENT_SECRET", default="")
if not DEBUG:
    # Prefer the *_PROD pair, but coalesce empty strings to the base value — the
    # compose file always *sets* the *_PROD vars (possibly to ""), and an empty
    # env var is "present" to django-environ, so a plain default= wouldn't kick in.
    GITHUB_OAUTH_CLIENT_ID = env("GITHUB_OAUTH_CLIENT_ID_PROD", default="") or GITHUB_OAUTH_CLIENT_ID
    GITHUB_OAUTH_CLIENT_SECRET = (
        env("GITHUB_OAUTH_CLIENT_SECRET_PROD", default="") or GITHUB_OAUTH_CLIENT_SECRET
    )
GITHUB_OAUTH_SCOPES = env("GITHUB_OAUTH_SCOPES", default="read:user,public_repo")

# Public base URL of the frontend, used to build the OAuth redirect URI.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# Realtime gateway (Rust service). When REALTIME_URL is empty, publishing
# activity events is a no-op, so the app runs fine without the gateway.
REALTIME_URL = env("REALTIME_URL", default="")
REALTIME_INTERNAL_TOKEN = env("REALTIME_INTERNAL_TOKEN", default="")
