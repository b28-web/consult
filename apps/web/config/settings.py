"""
Django settings for Consult.

Secrets come from Doppler - never hardcode credentials.
Run with: doppler run -- uv run python manage.py runserver
"""

from pathlib import Path

import environ  # type: ignore[import-untyped]

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environ
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local apps
    "apps.web.core",
    "apps.web.inbox",
    "apps.web.crm",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom middleware
    "apps.web.core.middleware.ClientMiddleware",
]

ROOT_URLCONF = "apps.web.config.urls"

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

WSGI_APPLICATION = "apps.web.config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
# Connection string from Doppler: DATABASE_URL
DATABASES = {
    "default": env.db("DATABASE_URL"),
}

# Custom user model
AUTH_USER_MODEL = "core.User"

# Password validation
_V = "django.contrib.auth.password_validation"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"{_V}.UserAttributeSimilarityValidator"},
    {"NAME": f"{_V}.MinimumLengthValidator"},
    {"NAME": f"{_V}.CommonPasswordValidator"},
    {"NAME": f"{_V}.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR.parent.parent / "staticfiles"  # /app/staticfiles in production

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
