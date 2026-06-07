# build v6
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV RAILWAY_CACHE_BUST="20260604v3"
COPY . .

RUN rm -f gunicorn.conf.py && echo "Build ok: $(date)"

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["sh", "-c", "exec gunicorn Deportes360.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --access-logfile - --error-logfile - --log-level info"]
