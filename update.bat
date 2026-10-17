@echo off
chcp 65001 >nul
cd /d "%~dp0"
git pull
if exist .venv .venv\Scripts\python -m pip install -r requirements-app.txt
echo Готово. Запустите start.bat.
pause
