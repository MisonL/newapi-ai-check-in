FROM node:20-bookworm-slim AS web-build

WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web .
RUN npm run build

FROM node:20-bookworm-slim

WORKDIR /app

ARG TARGETARCH
ARG CAMOUFOX_VERSION=135.0.1
ARG CAMOUFOX_RELEASE=beta.24

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH \
    CONTROL_PLANE_HOST=127.0.0.1 \
    CONTROL_PLANE_PORT=18080 \
    CONTROL_PLANE_BASE_URL=http://127.0.0.1:18080 \
    CONTROL_PLANE_STORAGE_MODE=persistent \
    CONTROL_PLANE_DATA_DIR=/app/runtime_data \
    NITRO_HOST=0.0.0.0 \
    NITRO_PORT=39327

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        fonts-liberation \
        gcc \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcairo2 \
        libdbus-glib-1-2 \
        libdrm2 \
        libgbm1 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libpango-1.0-0 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        libxtst6 \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN python3 -m venv /tmp/uv-bootstrap \
    && /tmp/uv-bootstrap/bin/pip install --no-cache-dir uv \
    && /tmp/uv-bootstrap/bin/uv sync --frozen --no-dev --python /usr/bin/python3 \
    && case "$TARGETARCH" in \
        amd64) export CAMOUFOX_ARCH=x86_64 ;; \
        arm64) export CAMOUFOX_ARCH=arm64 ;; \
        *) echo "Unsupported camoufox arch: $TARGETARCH" >&2; exit 1 ;; \
       esac \
    && export CAMOUFOX_VERSTR="${CAMOUFOX_VERSION}-${CAMOUFOX_RELEASE}" \
    && export CAMOUFOX_URL="https://github.com/daijro/camoufox/releases/download/v${CAMOUFOX_VERSTR}/camoufox-${CAMOUFOX_VERSTR}-lin.${CAMOUFOX_ARCH}.zip" \
    && .venv/bin/python -c "import os, shutil, tempfile, orjson; from camoufox.pkgman import INSTALL_DIR, unzip, webdl; camoufox_version = os.environ['CAMOUFOX_VERSION']; camoufox_release = os.environ['CAMOUFOX_RELEASE']; camoufox_url = os.environ['CAMOUFOX_URL']; shutil.rmtree(INSTALL_DIR, ignore_errors=True); INSTALL_DIR.mkdir(parents=True, exist_ok=True); archive_file = tempfile.NamedTemporaryFile(); webdl(camoufox_url, buffer=archive_file); unzip(archive_file, str(INSTALL_DIR)); archive_file.close(); (INSTALL_DIR / 'version.json').write_bytes(orjson.dumps({'version': camoufox_version, 'release': camoufox_release}))" \
    && chmod -R 755 /root/.cache/camoufox \
    && rm -rf /tmp/uv-bootstrap

COPY . .
COPY --from=web-build /app/web/.output /app/web/.output

EXPOSE 39327

CMD ["bash", "scripts/start-stack.sh"]
