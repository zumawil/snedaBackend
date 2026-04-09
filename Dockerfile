# Use official Python slim image for production
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_DEBUG False

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Run static files collection
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Use Gunicorn as the production application server
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "snedaEcommerceAPI.wsgi:application"]
