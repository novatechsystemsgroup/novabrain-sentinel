# NovaBrain Sentinel — single-container vertical slice
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Coolify runs its HTTP healthcheck with curl/wget inside this container; python:3.13-slim ships neither.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sentinel/ sentinel/
COPY static/ static/

# Run as an unprivileged, non-root user.
RUN useradd --uid 10001 --user-group --create-home --shell /usr/sbin/nologin sentinel
USER 10001

ENV SENTINEL_HOST=0.0.0.0 \
    SENTINEL_PORT=8000 \
    SENTINEL_LOG_LEVEL=info \
    SENTINEL_ENV=production

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import os,sys,urllib.request; url='http://127.0.0.1:'+os.environ.get('SENTINEL_PORT','8000')+'/health'; sys.exit(0 if urllib.request.urlopen(url, timeout=3).status==200 else 1)"]

CMD ["sh", "-c", "exec python -m uvicorn sentinel.api:app --host \"$SENTINEL_HOST\" --port \"$SENTINEL_PORT\" --log-level \"$SENTINEL_LOG_LEVEL\""]
