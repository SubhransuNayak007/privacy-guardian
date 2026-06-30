@echo off
cd /d "%~dp0"
start /b npx localtunnel --port 8000 --subdomain sweet-shirts-sneeze
cd python-engine
"venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
