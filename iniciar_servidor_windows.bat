@echo off
cd /d "%~dp0"
py -3 launch_server.py
if errorlevel 1 pause
