FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=false

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN DJANGO_SECRET_KEY=build-only-collectstatic JWT_SECRET=build-only python manage.py collectstatic --noinput

RUN useradd --create-home app && mkdir -p /app/uploads && chown -R app /app/uploads
USER app

EXPOSE 8000
# Migrations run on start so a fresh container is usable; seed separately:
#   docker compose exec api python manage.py seed   (Railway: railway ssh)
# PORT is set by hosts such as Railway; 8000 otherwise.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-3} --access-logfile -"]
