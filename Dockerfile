FROM node:20-bookworm-slim AS web-build

WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web .
RUN npm run build

FROM node:20-bookworm-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH \
    CONTROL_PLANE_HOST=127.0.0.1 \
    CONTROL_PLANE_PORT=18080 \
    CONTROL_PLANE_BASE_URL=http://127.0.0.1:18080 \
    CONTROL_PLANE_STORAGE_MODE=persistent \
    CONTROL_PLANE_DATA_DIR=/app/runtime_data \
    NITRO_HOST=0.0.0.0 \
    NITRO_PORT=3000

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip python3-venv python3-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN python3 -m venv /tmp/uv-bootstrap \
    && /tmp/uv-bootstrap/bin/pip install --no-cache-dir uv \
    && /tmp/uv-bootstrap/bin/uv sync --frozen --no-dev --python /usr/bin/python3 \
    && rm -rf /tmp/uv-bootstrap

COPY . .
COPY --from=web-build /app/web/.output /app/web/.output

EXPOSE 3000

CMD ["bash", "scripts/start-stack.sh"]
