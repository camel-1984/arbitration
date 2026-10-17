@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python не найден. Установите Python 3.12 с https://www.python.org/downloads/ и запустите start.bat снова.
  pause
  exit /b 1
)
if not exist .venv (
  echo Первый запуск: устанавливаю программу, это займёт несколько минут...
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo Нужен именно Python 3.12: https://www.python.org/downloads/release/python-3129/
    pause
    exit /b 1
  )
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements-app.txt
  if errorlevel 1 (
    echo Не удалось установить зависимости. Пришлите скриншот этого окна.
    rmdir /s /q .venv
    pause
    exit /b 1
  )
)
echo Сайт открывается в браузере: http://localhost:8001
echo Не закрывайте это окно, пока работаете. Чтобы выключить, закройте его.
start "" cmd /c "timeout /t 5 >nul & start http://localhost:8001"
set PYTHONPATH=%cd%
.venv\Scripts\python -m uvicorn src.api.app:app --port 8001
pause
