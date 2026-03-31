#!/usr/bin/env bash
set -euo pipefail

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Python virtual environment is missing. Run 'uv sync --dev' or build the Docker image first." >&2
  exit 1
fi

if [[ ! -f "web/.output/server/index.mjs" ]]; then
  echo "Nuxt production bundle is missing. Run 'npm install && npm run build' in web/ first." >&2
  exit 1
fi

cleanup() {
  if [[ -n "${PY_PID:-}" ]]; then
    kill "${PY_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

.venv/bin/python control_plane_main.py &
PY_PID=$!

wait_for_control_plane() {
  local attempts=60
  local delay=1
  local url="http://127.0.0.1:${CONTROL_PLANE_PORT:-18080}/health"

  for ((i=1; i<=attempts; i++)); do
    if python3 - <<PY
from urllib.error import URLError
from urllib.request import urlopen

try:
    with urlopen("${url}", timeout=2) as response:
        raise SystemExit(0 if response.status == 200 else 1)
except URLError:
    raise SystemExit(1)
PY
    then
      return 0
    fi

    if ! kill -0 "${PY_PID}" 2>/dev/null; then
      echo "Control plane exited before becoming ready." >&2
      return 1
    fi

    sleep "${delay}"
  done

  echo "Timed out waiting for control plane readiness at ${url}." >&2
  return 1
}

wait_for_control_plane

node web/.output/server/index.mjs
