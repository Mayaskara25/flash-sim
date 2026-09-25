#!/usr/bin/env bash
# P2 Risk Engine — Linux/macOS equivalent of start.ps1.
#
# Sets up the backend venv and frontend node_modules if missing, then runs
# uvicorn (port 8000) and `npm run dev` (port 5173) together. Ctrl-C stops
# both.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "==> Creating backend venv"
  python3 -m venv "$BACKEND_DIR/.venv"
fi

echo "==> Installing backend dependencies"
"$BACKEND_DIR/.venv/bin/pip" install -q -r "$BACKEND_DIR/requirements.txt"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "==> Installing frontend dependencies"
  (cd "$FRONTEND_DIR" && npm install)
fi

PIDS=()

cleanup() {
  echo ""
  echo "==> Shutting down"
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "==> Starting backend (uvicorn, port 8000)"
(cd "$BACKEND_DIR" && exec "$BACKEND_DIR/.venv/bin/python" -m uvicorn main:app --reload --port 8000) &
PIDS+=($!)

echo "==> Starting frontend (vite, port 5173)"
(cd "$FRONTEND_DIR" && exec npm run dev) &
PIDS+=($!)

wait
