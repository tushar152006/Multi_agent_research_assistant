@echo off
echo =======================================================
echo  Starting Multi-Agent Autonomous Research Assistant
echo =======================================================

echo [1/2] Launching FastAPI Backend on http://localhost:8000 ...
start "Backend Server" cmd /k "call .venv\Scripts\activate.bat && uvicorn backend.api.main:app --reload --port 8000"

echo [2/2] Launching Next.js Frontend on http://localhost:3000 ...
start "Frontend Dashboard" cmd /k "cd frontend && npm run dev"

echo.
echo All services launched!
echo - Web Dashboard:  http://localhost:3000
echo - API Docs / SWAG: http://localhost:8000/docs
echo - WebSocket:      ws://localhost:8000/ws/research
echo =======================================================
pause
