@echo off
cd /d "%~dp0"
python run_as_admin.py
if errorlevel 1 pause
