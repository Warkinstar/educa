from .base import *
import os

DEBUG = False


# Send traceback in email if error
ADMINS = [
    ("Ramil Sh", "Warkinstar@gmail.com"),
]

ALLOWED_HOSTS = ["educaproject.com", "www.educaprojet.com"]

DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("POSTGRES_DB"),
    "USER": os.environ.get("POSTGRES_USER"),
    "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
    "HOST": "db",
    "PORT": 5432,
}}

# Update REDIS_URL on dockerized redis
REDIS_URL = "redis://cache:6379"  # Служебное имя = "cache"
CACHES["default"]["LOCATION"] = REDIS_URL
CHANNEL_LAYERS["default"]["CONFIG"]["host"] = REDIS_URL


# Security
CSRF_COOKIE_SECURE = True  # only transfer the cookie over HTTPS
SESSION_COOKIE_SECURE = True  # Use a secure session cookie over HTTPS
SECURE_SSL_REDIRECT = True  # HTTP requests have to be redirected to HTTPS