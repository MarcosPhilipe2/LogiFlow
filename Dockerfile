FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////dados/logiflow.db \
    PORT=8000

WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 logiflow \
    && useradd --uid 10001 --gid logiflow --no-log-init --create-home logiflow \
    && mkdir /dados \
    && chown logiflow:logiflow /dados

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts
COPY docker ./docker

USER logiflow
EXPOSE 8000
VOLUME ["/dados"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "/app/docker/healthcheck.py"]
ENTRYPOINT ["python", "/app/docker/iniciar.py"]
