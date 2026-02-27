"""
DRP History — saves each prediction result to data/drp_history.json
"""
import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
HISTORY_FILE = os.path.join(DATA_DIR, "drp_history.json")


def _load() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError):
        return []


def _save(data: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_prediction(result: dict):
    history = _load()
    entry = dict(result)
    entry["saved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry["id"] = max((h["id"] for h in history), default=0) + 1
    history.insert(0, entry)          # newest first
    history = history[:100]           # keep last 100
    _save(history)


def get_history() -> list:
    return _load()


def delete_history_entry(entry_id: int):
    history = [h for h in _load() if h["id"] != entry_id]
    _save(history)


def clear_history():
    _save([])
