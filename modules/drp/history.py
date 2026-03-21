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


def mark_prediction_completed(entry_id: int, actual_hours: float, completed_on: str) -> dict | None:
    history = _load()
    updated = None
    for entry in history:
        if entry.get("id") != entry_id:
            continue
        entry["actual_hours"] = round(float(actual_hours), 2)
        entry["completed_on"] = completed_on
        updated = entry
        break
    if updated:
        _save(history)
    return updated


def get_accuracy_report() -> dict:
    entries = _load()
    completed = [
        e for e in entries
        if e.get("actual_hours") is not None and e.get("completed_on") and e.get("adjusted_hours") not in (None, 0)
    ]

    if not completed:
        return {
            "count": 0,
            "mean_abs_error_pct": 0.0,
            "mean_bias_pct": 0.0,
            "brier_score": 0.0,
            "bucket_accuracy": {
                "low": {"count": 0, "predicted_miss_pct": 0.0, "actual_miss_pct": 0.0},
                "medium": {"count": 0, "predicted_miss_pct": 0.0, "actual_miss_pct": 0.0},
                "high": {"count": 0, "predicted_miss_pct": 0.0, "actual_miss_pct": 0.0},
            },
            "recent_rows": [],
        }

    abs_errors = []
    signed_errors = []
    brier_values = []
    bucket_rows = {
        "low": [],
        "medium": [],
        "high": [],
    }
    recent = []

    for e in completed:
        adjusted = float(e.get("adjusted_hours", 0.0) or 0.0)
        actual = float(e.get("actual_hours", 0.0) or 0.0)
        if adjusted <= 0:
            continue

        err = (actual - adjusted) / adjusted
        abs_errors.append(abs(err) * 100)
        signed_errors.append(err * 100)

        predicted_miss = float(e.get("miss_probability", 0.0) or 0.0) / 100.0
        deadline_raw = e.get("deadline")
        completed_raw = e.get("completed_on")
        try:
            deadline_dt = datetime.strptime(deadline_raw, "%Y-%m-%d").date() if deadline_raw else None
            completed_dt = datetime.strptime(completed_raw, "%Y-%m-%d").date() if completed_raw else None
            missed = 1.0 if (deadline_dt and completed_dt and completed_dt > deadline_dt) else 0.0
        except ValueError:
            missed = 0.0

        brier_values.append((predicted_miss - missed) ** 2)

        if predicted_miss < 0.3:
            bucket = "low"
        elif predicted_miss < 0.6:
            bucket = "medium"
        else:
            bucket = "high"
        bucket_rows[bucket].append((predicted_miss * 100.0, missed * 100.0))

        recent.append({
            "task_name": e.get("task_name", "Unnamed Task"),
            "saved_at": e.get("saved_at", ""),
            "miss_probability": round(predicted_miss * 100.0, 1),
            "actual_missed": bool(missed),
            "adjusted_hours": round(adjusted, 2),
            "actual_hours": round(actual, 2),
            "error_pct": round(err * 100.0, 1),
        })

    def _bucket_metrics(rows: list[tuple[float, float]]) -> dict:
        if not rows:
            return {"count": 0, "predicted_miss_pct": 0.0, "actual_miss_pct": 0.0}
        predicted_avg = sum(r[0] for r in rows) / len(rows)
        actual_avg = sum(r[1] for r in rows) / len(rows)
        return {
            "count": len(rows),
            "predicted_miss_pct": round(predicted_avg, 1),
            "actual_miss_pct": round(actual_avg, 1),
        }

    recent_sorted = sorted(recent, key=lambda item: item.get("saved_at", ""), reverse=True)[:15]
    return {
        "count": len(recent),
        "mean_abs_error_pct": round(sum(abs_errors) / len(abs_errors), 1) if abs_errors else 0.0,
        "mean_bias_pct": round(sum(signed_errors) / len(signed_errors), 1) if signed_errors else 0.0,
        "brier_score": round(sum(brier_values) / len(brier_values), 3) if brier_values else 0.0,
        "bucket_accuracy": {
            "low": _bucket_metrics(bucket_rows["low"]),
            "medium": _bucket_metrics(bucket_rows["medium"]),
            "high": _bucket_metrics(bucket_rows["high"]),
        },
        "recent_rows": recent_sorted,
    }
