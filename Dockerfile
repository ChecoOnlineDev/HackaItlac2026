# syntax=docker/dockerfile:1
# Un solo desplegable (ADR-002): FastAPI entrega la API bajo /api y la interfaz ya construida.
# Construir: docker compose build   |   Sin secretos dentro: todo llega por variables de entorno.

# ---- Etapa 1: construye la interfaz (aplicación de una sola página) ----
FROM node:24-alpine AS interfaz
# Versión de pnpm con la que se generó frontend/pnpm-lock.yaml (lockfileVersion 9).
RUN corepack enable && corepack prepare pnpm@10.27.0 --activate
WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

# ---- Etapa 2: instala el backend con uv (solo dependencias de producción) ----
FROM python:3.14-slim AS backend
COPY --from=ghcr.io/astral-sh/uv:0.9.22 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---- Etapa 3: imagen final, delgada y sin root ----
FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    INTERFAZ_DIR=/app/interfaz \
    ARCHIVOS_DIR=/data/archivos

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin imhotep \
    && mkdir -p /data/archivos \
    && chown -R imhotep:imhotep /data

WORKDIR /app
COPY --from=backend /app/.venv /app/.venv
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY --from=interfaz /frontend/build/client ./interfaz

# Arranque: migra (reintenta si la base aún no está lista), carga datos de prueba si se pide
# y sirve. Va detrás del túnel de Cloudflare (HTTPS): se confía en sus cabeceras X-Forwarded-*.
COPY --chmod=755 <<'EOF' /usr/local/bin/arrancar
#!/bin/sh
set -eu
intento=0
until alembic upgrade head; do
  intento=$((intento + 1))
  if [ "$intento" -ge 30 ]; then
    echo "La base de datos no quedó lista después de $intento intentos." >&2
    exit 1
  fi
  echo "Esperando a la base de datos (intento $intento de 30)..." >&2
  sleep 2
done
if [ "${CARGAR_DATOS_PRUEBA:-false}" = "true" ]; then
  python -m app.datos_prueba
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
  --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"
EOF

USER imhotep
EXPOSE 8000
VOLUME ["/data/archivos"]
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD ["python", "-c", "import sys,urllib.request as u; sys.exit(0 if u.urlopen('http://127.0.0.1:8000/api/salud', timeout=4).status == 200 else 1)"]
CMD ["arrancar"]
