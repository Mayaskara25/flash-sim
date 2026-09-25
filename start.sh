#!/usr/bin/env bash
# P2 Risk Engine — Linux/macOS equivalent of start.ps1.
#
# Uses dependencies installed before the demo; never downloads on stage.
# Runs uvicorn (port 8000) and Vite (port 5173) together. Ctrl-C stops both.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -x "$BACKEND_DIR/.venv/bin/python" ]; then
  echo "Backend environment missing. Before the demo, run: python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt" >&2
  exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Frontend dependencies missing. Before the demo, run: cd frontend && npm ci" >&2
  exit 1
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
