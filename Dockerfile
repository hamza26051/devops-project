# ╔══════════════════════════════════════════════════════════════════╗
# ║          VeriDrive Inference Server — Production Dockerfile      ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Multi-stage build:                                              ║
# ║    Stage 1 (builder) — compiles wheels, never ships to prod      ║
# ║    Stage 2 (runtime) — lean image, non-root, health-checked      ║
# ║                                                                  ║
# ║  Security surface eliminated vs original:                        ║
# ║    - Firebase .json credentials NOT baked into image             ║
# ║    - Training data / labeled_data.csv NOT copied                 ║
# ║    - MLflow artifacts / .db files NOT copied                     ║
# ║    - gcc and build tools NOT present in runtime layer            ║
# ║    - Process runs as uid 1001 (appuser), never root              ║
# ╚══════════════════════════════════════════════════════════════════╝

# ──────────────────────────────────────────────────────────────────
# Stage 1 — Builder
# Installs all Python dependencies into /install prefix.
# This layer and its build tools are DISCARDED before the final image.
# ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Build tools needed only to compile C extensions (scipy, numpy).
# Installed here; absent from the runtime image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install into an isolated prefix so Stage 2 can copy them cleanly.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ──────────────────────────────────────────────────────────────────
# Stage 2 — Runtime
# Minimal Python image; receives only the installed packages and
# the application source. No build tools, no credentials, no data.
# ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# ── Runtime configuration ─────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    APP_ENV=production \
    TRANSFORMERS_CACHE=/app/cache

WORKDIR /app

# ── Installed packages from builder stage ─────────────────────────
COPY --from=builder /install /usr/local

# ── Application source (inference-only files) ─────────────────────
COPY main.py risk_engine.py firebase_service.py config.py ./

# ── Non-root user & Permissions ───────────────────────────────────
RUN groupadd --gid 1001 appgroup \
 && useradd  --uid 1001 --gid appgroup --create-home --shell /bin/bash appuser \
 && mkdir -p /app/cache \
 && chown -R appuser:appgroup /app

# ── Health check ──────────────────────────────────────────────────
# Increase start-period to 300s (5 mins) to allow for model download
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD python -c \
        "import urllib.request, os, sys; \
         port = os.environ.get('PORT', '8000'); \
         r = urllib.request.urlopen(f'http://localhost:{port}/health', timeout=8); \
         sys.exit(0 if r.status == 200 else 1)"

# Drop to non-root before the process starts
USER appuser

EXPOSE 8000

# Use the dynamic PORT variable provided by the environment
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 4"]