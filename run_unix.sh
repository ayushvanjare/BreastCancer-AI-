#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "BreastCare AI - Phase 2.1 local launcher"
command -v python3 >/dev/null || { echo "Python 3.11/3.12 is required"; exit 1; }
command -v node >/dev/null || { echo "Node.js 20+ is required"; exit 1; }
if [[ ! -x backend/.venv/bin/python ]]; then python3 -m venv backend/.venv; fi
backend/.venv/bin/python -m pip install -r backend/requirements.txt
if [[ ! -d frontend/node_modules ]]; then (cd frontend && npm install); fi
( cd backend && ../backend/.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 ) &
API_PID=$!
( cd frontend && npm run dev -- --host 127.0.0.1 ) &
FRONTEND_PID=$!
trap 'kill "$API_PID" "$FRONTEND_PID" 2>/dev/null || true' EXIT INT TERM
echo "Frontend: http://localhost:5173"
echo "API docs: http://127.0.0.1:8000/docs"
wait
