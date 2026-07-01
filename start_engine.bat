@echo off
cd /d "%~dp0"
start /b node tunnel_manager.js
cd python-engine
"venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
