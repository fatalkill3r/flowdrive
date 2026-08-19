import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-only-key")
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
ALLOWED_HOSTS = [x.strip() for x in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,10.81.2.81,testserver").split(",") if x.strip()]
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "apps.accounts", "apps.files", "apps.dashboard", "apps.activity", "apps.sharing", "apps.notifications", "apps.audit", "apps.adminpanel", "apps.file_requests",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages", "apps.dashboard.context_processors.branding", "apps.notifications.context_processors.notifications"]}}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}, {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}]
LANGUAGE_CODE = "en-us"; TIME_ZONE = "UTC"; USE_I18N = True; USE_TZ = True
STATIC_URL = "static/"; STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "accounts:login"; LOGIN_REDIRECT_URL = "dashboard:home"; LOGOUT_REDIRECT_URL = "accounts:login"
FILEBOX_STORAGE_ROOT = Path(os.getenv("FILEBOX_STORAGE_ROOT", BASE_DIR / "storage"))
if not FILEBOX_STORAGE_ROOT.is_absolute(): FILEBOX_STORAGE_ROOT = BASE_DIR / FILEBOX_STORAGE_ROOT
FILEBOX_MAX_UPLOAD_BYTES = int(os.getenv("FILEBOX_MAX_UPLOAD_BYTES", 500 * 1024 * 1024))
FILEBOX_DEFAULT_QUOTA_BYTES = int(os.getenv("FILEBOX_DEFAULT_QUOTA_BYTES", 10 * 1024**3))
FILEBOX_MAX_FILE_VERSIONS = int(os.getenv("FILEBOX_MAX_FILE_VERSIONS", 20))
FILEBOX_TRASH_RETENTION_DAYS = int(os.getenv("FILEBOX_TRASH_RETENTION_DAYS", 30))
FILEBOX_UPLOAD_REQUESTS_ENABLED = os.getenv("FILEBOX_UPLOAD_REQUESTS_ENABLED", "True").lower() == "true"
FILEBOX_MAX_REQUEST_DAYS = int(os.getenv("FILEBOX_MAX_REQUEST_DAYS", 30))
LOGGING = {"version": 1, "disable_existing_loggers": False, "handlers": {"file": {"class": "logging.FileHandler", "filename": BASE_DIR / "logs/application.log", "level": "INFO"}}, "loggers": {"filebox": {"handlers": ["file"], "level": "INFO", "propagate": False}}}
