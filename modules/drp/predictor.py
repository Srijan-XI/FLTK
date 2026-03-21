"""
Deadline Risk Predictor (DRP)
Calculates the probability of missing a deadline based on task complexity,
historical performance, and current workload.
"""

from datetime import date, datetime, timedelta
import math


def predict(task_name: str, estimated_hours: float, deadline_str: str,
            past_speed: float, daily_workload: float,
            working_hours_per_day: float = 8.0,
            include_weekends: bool = False,
            unavailable_dates: set[str] | None = None,
            linked_context: dict | None = None) -> dict:
    """
    Parameters
    ----------
    task_name       : name / description of the task
    estimated_hours : total work hours the task requires
    deadline_str    : deadline date in 'YYYY-MM-DD' format
    past_speed      : historical on-time completion rate  0-100 (%)
    daily_workload  : hours already committed per working day (other tasks)

    Returns
    -------
    dict with keys:
        task_name, risk_level, miss_probability, available_hours,
        adjusted_hours, days_left, recommended_daily_hours, schedule_advice, alerts,
        deadline, available_days, calendar_summary, linked_context
    """

    today = date.today()
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid deadline format. Use YYYY-MM-DD."}

    days_left = (deadline - today).days
    unavailable = unavailable_dates or set()

    # ── Edge cases ──────────────────────────────────────────────────────────
    alerts = []
    if days_left < 0:
        return {
            "task_name": task_name,
            "risk_level": "CRITICAL",
            "miss_probability": 100,
            "days_left": days_left,
            "deadline": deadline.isoformat(),
            "available_hours": 0,
            "available_days": 0,
            "adjusted_hours": round(estimated_hours, 2),
            "recommended_daily_hours": None,
            "schedule_advice": "Deadline has already passed.",
            "alerts": ["Deadline has already passed!"],
            "calendar_summary": {
                "include_weekends": include_weekends,
                "blocked_days": 0,
                "working_days_considered": 0,
            },
            "linked_context": linked_context or {},
        }

    if days_left == 0:
        alerts.append("Deadline is today!")

    # ── Core calculation ─────────────────────────────────────────────────────
    working_day_count = _count_working_days(today, deadline, include_weekends, unavailable)
    effective_daily = max(float(working_hours_per_day) - daily_workload, 0.5)
    available_hours = effective_daily * working_day_count

    # Adjust estimated hours for historical under-performance
    speed_factor = max(past_speed / 100, 0.1)   # floor at 10 % to avoid ÷0
    adjusted_hours = estimated_hours / speed_factor

    # Ratio: how much cushion do we have?
    if adjusted_hours == 0:
        ratio = float("inf")
    else:
        ratio = available_hours / adjusted_hours

    miss_probability = _ratio_to_probability(ratio)
    risk_level = _probability_to_risk(miss_probability)

    # Build alerts
    if daily_workload >= float(working_hours_per_day):
        alerts.append("Your current workload already fills a full workday — no buffer left.")
    if past_speed < 60:
        alerts.append("Historical completion rate below 60 % — consider revising your estimate.")
    if days_left <= 2 and miss_probability > 50:
        alerts.append("Very little time remaining. Consider negotiating the deadline.")

    # Recommended daily hours to finish on time
    if working_day_count > 0:
        recommended_daily = math.ceil((adjusted_hours / working_day_count) * 10) / 10
    else:
        recommended_daily = None

    schedule_advice = _build_advice(ratio, recommended_daily, daily_workload, past_speed)
    if working_day_count == 0 and days_left >= 0:
        alerts.append("No working days are available before the deadline with current calendar settings.")

    return {
        "task_name": task_name,
        "risk_level": risk_level,
        "miss_probability": round(miss_probability, 1),
        "days_left": days_left,
        "deadline": deadline.isoformat(),
        "available_hours": round(available_hours, 2),
        "available_days": working_day_count,
        "adjusted_hours": round(adjusted_hours, 2),
        "recommended_daily_hours": recommended_daily,
        "schedule_advice": schedule_advice,
        "alerts": alerts,
        "calendar_summary": {
            "include_weekends": include_weekends,
            "blocked_days": len(unavailable),
            "working_days_considered": working_day_count,
        },
        "linked_context": linked_context or {},
    }


# ── Helper functions ──────────────────────────────────────────────────────────

def _ratio_to_probability(ratio: float) -> float:
    """
    Smooth sigmoid-based miss probability.
    ratio = available_hours / adjusted_hours
      ratio > 1  → comfortable (low miss probability)
      ratio < 1  → overloaded  (high miss probability)
    Uses a logistic curve centered at ratio=1 and clamped to [3, 97].
    """
    if ratio == float("inf"):
        return 3.0
    # Steepness k=4 gives ~5% at ratio=2.0 and ~95% at ratio=0.0
    k = 4.0
    raw = 1.0 / (1.0 + math.exp(k * (ratio - 1.0)))
    # raw is in (0,1): 0 → very safe, 1 → very risky; mirror so high ratio = low risk
    miss = (1 - raw) * 100
    # flip: high ratio means LESS miss probability
    miss = raw * 100
    return round(max(3.0, min(97.0, miss)), 1)


def _probability_to_risk(prob: float) -> str:
    if prob < 30:
        return "LOW"
    if prob < 55:
        return "MEDIUM"
    if prob < 75:
        return "HIGH"
    return "CRITICAL"


def _build_advice(ratio: float, rec_daily: float | None,
                  workload: float, past_speed: float) -> str:
    parts = []
    if ratio >= 1.5:
        parts.append("You have comfortable time — maintain steady progress.")
    elif ratio >= 1.0:
        parts.append("On track, but don't slack off.")
    elif ratio >= 0.75:
        parts.append("Tight schedule — reduce other commitments if possible.")
    else:
        parts.append("Overloaded — consider requesting a deadline extension.")

    if rec_daily is not None:
        parts.append(f"Aim for {rec_daily} h/day on this task.")

    if past_speed < 80:
        parts.append("Boost focus time to improve your completion rate.")

    if workload > 4:
        parts.append("Try to offload or pause lower-priority tasks.")

    return " ".join(parts)


def _count_working_days(start: date, end: date, include_weekends: bool, unavailable_dates: set[str]) -> int:
    if end <= start:
        return 0
    total = 0
    cursor = start + timedelta(days=1)
    while cursor <= end:
        if not include_weekends and cursor.weekday() >= 5:
            cursor += timedelta(days=1)
            continue
        if cursor.isoformat() in unavailable_dates:
            cursor += timedelta(days=1)
            continue
        total += 1
        cursor += timedelta(days=1)
    return total
