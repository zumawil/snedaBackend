# 📦 Additional Dependencies for Production

**Current Requirements Version:** See `requirements.txt`
**Last Updated:** 2025-12-09

---

## 🚀 RECOMMENDED ADDITIONAL PACKAGES

### For Production Deployment

```bash
# Gunicorn - Production WSGI server
pip install gunicorn>=20.1.0

# PostgreSQL Database Adapter
pip install psycopg2-binary>=2.9.0

# WhiteNoise - Serve static files in production
pip install whitenoise>=6.0.0

# Environment variable management
pip install python-dotenv>=0.19.0  # (already in requirements.txt)
```

### For Email & SendGrid

```bash
# SendGrid email backend
pip install sendgrid-django>=4.2.0

# Or alternatively, for AWS SES:
pip install django-anymail[amazon_ses]>=8.0
```

### For Async Tasks (Celery)

```bash
# Celery for async tasks
pip install celery>=5.3.0
pip install redis>=4.0.0
pip install django-celery-beat>=2.5.0  # For scheduled tasks
pip install django-celery-results>=2.5.0  # To store task results
```

### For Caching

```bash
# Redis client
pip install redis>=4.5.0

# Django Redis wrapper
pip install django-redis>=5.2.0
```

### For Error Tracking

```bash
# Sentry error tracking
pip install sentry-sdk>=1.30.0
```

### For Rate Limiting & Security

```bash
# DRF-specific rate limiting
pip install djangorestframework-throttling>=0.1.0  # (optional, DRF has built-in)

# Security headers
pip install django-cors-headers>=4.0.0  # (already in requirements.txt)
```

### For Code Quality & Testing

```bash
# Testing
pip install pytest>=7.0.0
pip install pytest-django>=4.5.0
pip install pytest-cov>=4.0.0
pip install factory-boy>=3.2.0

# Code quality
pip install flake8>=6.0.0
pip install black>=23.0.0
pip install isort>=5.12.0
pip install mypy>=1.0.0

# Security scanning
pip install bandit>=1.7.0
```

### For Database Migrations & Admin

```bash
# Django extensions (optional but useful)
pip install django-extensions>=3.2.0

# Better admin interface (optional)
pip install django-admin-interface>=0.22.0
```

### For Monitoring & Analytics (Optional)

```bash
# Prometheus metrics
pip install django-prometheus>=2.2.0

# New Relic APM (optional, if using their service)
pip install newrelic>=8.8.0
```

---

## 📋 COMPLETE PRODUCTION requirements.txt

Create a new file `requirements-production.txt` with:

```
# Django & DRF
Django==5.2.8
djangorestframework==3.16.1
djangorestframework_simplejwt==5.5.1
drf-yasg==1.21.11

# Database
psycopg2-binary==2.9.0
django-redis==5.2.0
redis==4.5.0

# Email
sendgrid-django==4.2.0

# Async Tasks
celery==5.3.0
django-celery-beat==2.5.0
django-celery-results==2.5.0

# Static Files & Deployment
whitenoise==6.0.0
gunicorn==21.2.0

# Security & CORS
django-cors-headers==4.9.0
django-environ==0.10.0

# Monitoring & Logging
sentry-sdk==1.30.0

# Testing (dev only)
pytest==7.4.0
pytest-django==4.5.0
pytest-cov==4.0.0
factory-boy==3.2.0

# Code Quality (dev only)
flake8==6.0.0
black==23.0.0
isort==5.12.0
mypy==1.0.0
bandit==1.7.0

# Utilities
Pillow==12.0.0
python-dotenv==1.2.1
pytz==2025.2
pyotp==2.9.0
PyJWT==2.10.1
requests==2.32.5

# Other
inflection==0.5.1
markdown-it-py==4.0.0
packaging==25.0
pydantic==2.0.0
```

---

## 🔧 INSTALLATION COMMANDS

### Install All Production Dependencies

```bash
# Create production environment
python -m venv venv_prod

# Activate
source venv_prod/bin/activate  # Linux/Mac
# or
venv_prod\Scripts\activate  # Windows

# Install production packages
pip install -r requirements.txt
pip install gunicorn psycopg2-binary whitenoise sendgrid-django celery redis django-celery-beat sentry-sdk
```

### Install Development Dependencies

```bash
# In addition to production packages:
pip install pytest pytest-django pytest-cov factory-boy
pip install flake8 black isort mypy bandit
```

---

## 📊 PACKAGE DEPENDENCY GRAPH

```
Core
├── Django 5.2.8
├── djangorestframework 3.16.1
├── djangorestframework-simplejwt 5.5.1
└── drf-yasg 1.21.11

Database
├── psycopg2-binary (PostgreSQL adapter)
├── redis
└── django-redis

Async Processing
├── celery
├── django-celery-beat
└── django-celery-results

Email
├── sendgrid-django
└── sendgrid

Static Files
├── whitenoise
├── pillow
└── django-storages (optional for S3)

Deployment
├── gunicorn
├── nginx (external)
└── supervisor/systemd (external)

Security
├── django-cors-headers
├── sentry-sdk
└── django-environ

Testing
├── pytest
├── pytest-django
├── pytest-cov
└── factory-boy

Code Quality
├── flake8
├── black
├── isort
├── mypy
└── bandit
```

---

## ⚠️ VERSION COMPATIBILITY

**Python:** 3.10+
**Django:** 5.2.x (LTS support until April 2026)
**PostgreSQL:** 12+
**Redis:** 6+

---

## 🚀 INSTALLATION ORDER

1. Core packages (Django, DRF, JWT)
2. Database packages (PostgreSQL, Redis)
3. Email packages (SendGrid)
4. Async packages (Celery, Redis)
5. Static file packages (WhiteNoise)
6. Deployment packages (Gunicorn)
7. Monitoring packages (Sentry)
8. Testing packages (pytest, etc.)
9. Code quality packages (flake8, black, etc.)

---

## 💡 QUICK START

```bash
# One-liner to install all production essentials
pip install gunicorn psycopg2-binary whitenoise sendgrid-django celery redis django-celery-beat sentry-sdk

# One-liner to install all testing/development tools
pip install pytest pytest-django pytest-cov factory-boy flake8 black isort mypy bandit
```

---

## 📝 NOTES

- All packages listed are compatible with Django 5.2.8
- Version numbers are recommendations; latest stable versions can usually be used
- Some packages are optional (e.g., django-admin-interface, newrelic)
- Always test new versions in staging environment first
- Keep requirements.txt updated with pinned versions for reproducibility

---

## 🔗 REFERENCES

- Package search: https://pypi.org/
- Django packages: https://djangopackages.org/
- Compatible packages: https://www.codepoint.dev/
- Security advisories: https://github.com/advisories
