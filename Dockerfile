# ── builder ───────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY src/pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
        "fastapi>=0.111.0" \
        "uvicorn[standard]>=0.30.0" \
        "prometheus-client>=0.20.0" \
        "pydantic>=2.7.0" \
    --target /deps

# ── runtime ───────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ARG MOVIES_VERSION=1.0.0
ENV MOVIES_VERSION=${MOVIES_VERSION}
ENV PYTHONPATH=/deps
ENV PYTHONUNBUFFERED=1

# non-root user
RUN useradd -u 1000 -m -s /sbin/nologin appuser

# Copy installed packages
COPY --from=builder /deps /deps

# Copy source
COPY src/movies_api /app/movies_api

# Bake data files
COPY src/data /data

WORKDIR /app
USER 1000

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"

CMD ["python3", "-m", "uvicorn", "movies_api.main:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8080", \
     "--no-access-log"]
