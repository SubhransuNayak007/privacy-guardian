@echo off
echo Stopping Privacy Guardian Backend...
taskkill /f /im python.exe /fi "WINDOWTITLE eq uvicorn" >nul 2>&1
taskkill /f /im node.exe /fi "COMMANDLINE eq *localtunnel*" >nul 2>&1
taskkill /f /im node.exe /fi "COMMANDLINE eq *tunnel_manager.js*" >nul 2>&1
wmic process where "commandline like '%%tunnel_manager.js%%'" call terminate >nul 2>&1
wmic process where "commandline like '%%localtunnel%%'" call terminate >nul 2>&1
echo Done.
pause
