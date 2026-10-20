FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home /app app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY scripts/ ./scripts/
COPY docker/ ./docker/

# /app/thumbs — volume WebP-превью (api/routers/img.py): заранее создаём от app, иначе свежий
# volume монтируется root-овым и API не может писать превью.
RUN chmod +x docker/entrypoint.sh && mkdir -p /app/thumbs && chown -R app:app /app
USER app

ENTRYPOINT ["docker/entrypoint.sh"]
