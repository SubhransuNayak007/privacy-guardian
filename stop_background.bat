@echo off
echo Stopping Privacy Guardian Backend...
taskkill /f /im python.exe /fi "WINDOWTITLE eq uvicorn" >nul 2>&1
taskkill /f /im node.exe /fi "COMMANDLINE eq *localtunnel*" >nul 2>&1
echo Done.
pause
