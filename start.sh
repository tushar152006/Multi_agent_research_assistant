#!/usr/bin/env bash
set -e

echo "======================================================="
echo " Starting Multi-Agent Autonomous Research Assistant"
echo "======================================================="

# Trap cleanup on exit
cleanup() {
    echo "Stopping all background processes..."
    kill $(jobs -p) 2>/dev/null || true
}
trap cleanup EXIT

echo "[1/2] Launching FastAPI Backend on http://localhost:8000 ..."
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null || true
uvicorn backend.api.main:app --reload --port 8000 &

echo "[2/2] Launching Next.js Frontend on http://localhost:3000 ..."
(cd frontend && npm run dev) &

echo "All services running in background."
echo "Dashboard: http://localhost:3000"
echo "API Docs:  http://localhost:8000/docs"
wait
