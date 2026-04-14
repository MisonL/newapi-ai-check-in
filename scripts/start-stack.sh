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
  if [[ -n "${XVFB_PID:-}" ]]; then
    kill "${XVFB_PID}" 2>/dev/null || true
  fi
  if [[ -n "${PY_PID:-}" ]]; then
    kill "${PY_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

start_xvfb() {
  local base_display="${XVFB_DISPLAY:-:99}"
  local base_number="${base_display#:}"
  local offset=0

  while [[ "${offset}" -lt 5 ]]; do
    local display=":$((base_number + offset))"
    local lock_file="/tmp/.X$((base_number + offset))-lock"
    local socket_file="/tmp/.X11-unix/X$((base_number + offset))"

    rm -f "${lock_file}" "${socket_file}"
    Xvfb "${display}" -screen 0 1280x1024x24 -ac +extension GLX -nolisten tcp >/tmp/xvfb.log 2>&1 &
    XVFB_PID=$!
    sleep 1

    if kill -0 "${XVFB_PID}" 2>/dev/null; then
      export DISPLAY="${display}"
      return 0
    fi

    offset=$((offset + 1))
  done

  return 1
}

python_command=(.venv/bin/python control_plane_main.py)
if [[ -z "${DISPLAY:-}" ]]; then
  if command -v Xvfb >/dev/null 2>&1; then
    if ! start_xvfb; then
      echo "Xvfb failed to start." >&2
      exit 1
    fi
  else
    echo "DISPLAY is not configured and Xvfb is unavailable." >&2
    exit 1
  fi
fi

"${python_command[@]}" &
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
