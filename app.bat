@echo off
title FLTK - Freelancer Toolkit

:: Create virtual environment if missing
if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found. Creating one...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Is Python installed?
        pause
        exit /b 1
    )
    echo [INFO] Installing dependencies...
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

:: Launch Flask app
echo Starting FLTK on http://127.0.0.1:5000 ...
python app.py

pause
