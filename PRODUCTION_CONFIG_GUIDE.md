# ⚙️ Production Configuration Checklist & Guide

**Last Updated:** 2025-12-09
**Purpose:** Step-by-step guide to harden your settings.py for production

---

## 🔴 CRITICAL CONFIGURATIONS (Must Fix First)

### 1. ENVIRONMENT VARIABLES

**Current Issue:** Hardcoded values in settings.py

**What to do:**
```bash
# Create/update your .env file with these variables:
DJANGO_DEBUG=False
SECRET_KEY=your-very-long-random-secret-key-here
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_CORS_ALLOWED_ORIGINS=https://your-frontend.com
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=sneda_ecommerce_db
DB_USER=sneda_user
DB_PASSWORD=strong-password-here
DB_HOST=localhost
DB_PORT=5432

# Email (SendGrid example)
EMAIL_BACKEND=sendgrid_backend.SendgridBackend
SENDGRID_API_KEY=your-sendgrid-api-key
EMAIL_HOST_USER=noreply@yourdomain.com

# Paystack
PAYSTACK_SECRET_KEY=your-paystack-secret-key
PAYSTACK_PUBLIC_KEY=your-paystack-public-key

# Sentry (Optional but recommended)
SENTRY_DSN=your-sentry-dsn-url
```

**In settings.py (lines 28-35), change to:**
```python
# Load environment variables
load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable not set!")

DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
```

---

### 2. HTTPS/SSL CONFIGURATION

**Current Issue:** All SSL settings are disabled (lines 253-257 in settings.py)

**Add these settings (new):**
```python
# Security settings for HTTPS/SSL
SECURE_SSL_REDIRECT = not DEBUG  # Redirect all HTTP to HTTPS in production
SECURE_HSTS_SECONDS = 31536000  # 1 year in seconds
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = not DEBUG  # Only send cookies over HTTPS
CSRF_COOKIE_SECURE = not DEBUG  # Only send CSRF cookie over HTTPS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY = {
    "default-src": ("'self'",),
    "script-src": ("'self'", "'unsafe-inline'"),
}
X_FRAME_OPTIONS = "DENY"
```

---

### 3. CORS CONFIGURATION

**Current Issue:** Set to localhost:3000 (lines 249-250)

**Replace lines 249-250 with:**
```python
# CORS settings - restrict to your frontend domain
CORS_ALLOWED_ORIGINS = os.environ.get('DJANGO_CORS_ALLOWED_ORIGINS', '').split(',')
CORS_ALLOW_CREDENTIALS = True  # Allow cookies to be sent with requests
```

---

### 4. DATABASE CONFIGURATION

**Current Issue:** Using SQLite (line 96-103)

**Replace DATABASES dict with:**
```python
DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.environ.get('DB_NAME', str(BASE_DIR / 'db.sqlite3')),
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
        
        # Connection pooling (if using PostgreSQL)
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Ensure we have PostgreSQL in production
if not DEBUG and 'postgresql' not in DATABASES['default']['ENGINE']:
    raise ValueError("PostgreSQL required for production!")
```

---

### 5. EMAIL CONFIGURATION

**Current Issue:** Using ConsoleEmailBackend (line 91)

**Replace with:**
```python
# Email Configuration
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    # Production: Use SendGrid or similar
    # First: pip install sendgrid-django
    EMAIL_BACKEND = "sendgrid_backend.SendgridBackend"
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
    SENDGRID_FROM_EMAIL = os.environ.get('EMAIL_HOST_USER', 'noreply@yourdomain.com')
    
    if not SENDGRID_API_KEY:
        raise ValueError("SENDGRID_API_KEY required in production!")

# Default email settings
DEFAULT_FROM_EMAIL = os.environ.get('EMAIL_HOST_USER', 'noreply@yourdomain.com')
SERVER_EMAIL = os.environ.get('EMAIL_HOST_USER', 'server@yourdomain.com')
```

---

### 6. LOGGING CONFIGURATION

**Current Issue:** Logging config exists but is commented out (lines 208+)

**Uncomment and update the LOGGING dict (lines 208-280)**

Or use this simplified version:
```python
# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] [{levelname}] {name} - {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file_error': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'errors.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 5,
            'formatter': 'verbose',
            'level': 'ERROR',
        },
    },
    'root': {
        'handlers': ['console', 'file_error'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file_error'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
```

---

## 🟡 IMPORTANT CONFIGURATIONS

### 7. ADD SENTRY INTEGRATION

**In settings.py (near the top):**
```python
# Sentry Error Tracking
if not DEBUG:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment=os.environ.get('ENVIRONMENT', 'production'),
    )
```

**In requirements.txt, add:**
```
sentry-sdk>=1.0.0
```

---

### 8. ADD RATE LIMITING

**In REST_FRAMEWORK config (around line 159):**
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "users.authentication.CookieJWTAuthentication",
    ),
    "EXCEPTION_HANDLER": "utils.exception_handler.custom_exception_handler",
    
    # Add throttling for rate limiting
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle"
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",  # 100 requests per day for anonymous users
        "user": "1000/day"  # 1000 requests per day for authenticated users
    }
}
```

---

### 9. ADD CACHING CONFIGURATION

**In settings.py (after DATABASES):**
```python
# Caching Configuration (requires Redis)
if not DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {'max_connections': 50}
            }
        }
    }
    
    # Use Redis for sessions too
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }
```

**In requirements.txt, add:**
```
django-redis>=5.0.0
redis>=4.0.0
```

---

### 10. ADD CELERY FOR ASYNC TASKS

**Create `snedaEcommerceAPI/celery.py`:**
```python
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'snedaEcommerceAPI.settings')

app = Celery('snedaEcommerceAPI')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
```

**In `snedaEcommerceAPI/__init__.py`, add:**
```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

**In requirements.txt, add:**
```
celery>=5.3.0
```

---

## 📋 CHECKLIST FOR PRODUCTION

- [ ] Create `.env` file with all required environment variables
- [ ] Fix duplicate DEBUG variable (lines 25 & 34)
- [ ] Update ALLOWED_HOSTS with your domain
- [ ] Configure CORS for your frontend domain
- [ ] Update DATABASE config for PostgreSQL
- [ ] Replace ConsoleEmailBackend with SendGrid/SES/Mailgun
- [ ] Uncomment LOGGING configuration
- [ ] Add HTTPS/SSL settings (SECURE_SSL_REDIRECT, etc.)
- [ ] Add Sentry integration
- [ ] Add rate limiting (throttling)
- [ ] Add caching configuration (Redis)
- [ ] Add Celery for async tasks
- [ ] Create `logs/` directory with proper permissions
- [ ] Test all configurations locally with DEBUG=False
- [ ] Run: `python manage.py check --deploy`
- [ ] Ensure `.env` is in `.gitignore`
- [ ] Ensure `logs/` is in `.gitignore`

---

## 🚀 COMMAND TO VALIDATE SETTINGS

After making changes, run:
```bash
python manage.py check --deploy
```

This will show any remaining issues with production settings.

---

## 📌 SUMMARY OF CHANGES NEEDED

| Line(s) | Current | Action |
|---------|---------|--------|
| 25, 34 | Duplicate DEBUG | Remove line 34, keep only line 25 |
| 28-35 | Hardcoded SECRET_KEY, DEBUG | Load from environment variables |
| 35 | Empty ALLOWED_HOSTS | Set from environment or hardcode domain |
| 91 | ConsoleEmailBackend | Replace with SendGrid/SES |
| 96-103 | SQLite database | Configure PostgreSQL |
| 159-165 | REST_FRAMEWORK config | Add throttling and other settings |
| 208-280 | Logging (commented) | Uncomment and verify |
| 249-250 | CORS to localhost | Set to production frontend domain |
| New | SSL settings | Add SECURE_SSL_REDIRECT, HSTS headers |
| New | Sentry integration | Add sentry_sdk configuration |

---

## 💡 HELPFUL COMMANDS

```bash
# Check for deploy issues
python manage.py check --deploy

# Create environment file
cp .env.example .env

# Run migrations on PostgreSQL
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Test sending email
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'This is a test', 'from@example.com', ['to@example.com'])

# Check database connection
python manage.py dbshell

# View installed apps
python manage.py showmigrations
```

---

## 📚 REFERENCES

- Django Deployment Checklist: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- Django Security: https://docs.djangoproject.com/en/5.2/topics/security/
- PostgreSQL Setup: https://www.postgresql.org/download/
- Sendgrid Django: https://github.com/sendgrid/sendgrid-django
- Celery Setup: https://docs.celeryproject.org/en/stable/django/

