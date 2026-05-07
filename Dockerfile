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

# ── Non-root user ─────────────────────────────────────────────────
# Running as root inside a container is an unnecessary privilege
# escalation risk. uid/gid 1001 is arbitrary but consistent.
RUN groupadd --gid 1001 appgroup \
 && useradd  --uid 1001 --gid appgroup --no-create-home --shell /sbin/nologin appuser

WORKDIR /app

# ── Installed packages from builder stage ─────────────────────────
COPY --from=builder /install /usr/local

# ── Application source (inference-only files) ─────────────────────
# .dockerignore prevents credentials, training data, and cache from
# ever reaching this COPY context. Belt-and-suspenders: we also
# name each file explicitly rather than using COPY . .
COPY main.py          ./
COPY risk_engine.py    ./
COPY firebase_service.py ./
COPY config.py           ./

# ── Model artifacts ───────────────────────────────────────────────
# In production these should be pulled from an artifact store
# (S3, GCS, DVC) at container startup, not baked into the image.
# They are included here for local development convenience.
# Override by mounting a volume: -v /host/models:/app/models
COPY toxicity_model_v3.pkl ./
COPY models/               ./models/
COPY sentiment_model/     ./sentiment_model/

# ── Runtime configuration ─────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    APP_ENV=production

# ── Health check ──────────────────────────────────────────────────
# Probes /health (added to main3.py). Container is marked unhealthy
# if the endpoint does not respond within 10 s.
# --start-period gives uvicorn 20 s to load the sklearn models.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c \
        "import urllib.request, sys; \
         r = urllib.request.urlopen('http://localhost:8000/health', timeout=8); \
         sys.exit(0 if r.status == 200 else 1)"

# Drop to non-root before the process starts
USER appuser

EXPOSE 8000

# Use Uvicorn with multiple workers for production scaling
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]