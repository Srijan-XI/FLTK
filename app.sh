#!/usr/bin/env bash
set -e

# Create virtual environment if missing
if [ ! -f ".venv/bin/activate" ]; then
    echo "[INFO] Virtual environment not found. Creating one..."
    python3 -m venv .venv || python -m venv .venv || { echo "[ERROR] Failed to create virtual environment. Is Python installed?"; exit 1; }
    echo "[INFO] Installing dependencies..."
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Launch Flask app
echo "Starting FLTK on http://127.0.0.1:5000 ..."
python app.py
