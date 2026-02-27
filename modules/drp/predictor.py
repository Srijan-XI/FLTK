"""
Deadline Risk Predictor (DRP)
Calculates the probability of missing a deadline based on task complexity,
historical performance, and current workload.
"""

from datetime import date, datetime
import math


def predict(task_name: str, estimated_hours: float, deadline_str: str,
            past_speed: float, daily_workload: float) -> dict:
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
        adjusted_hours, days_left, recommended_daily_hours, schedule_advice, alerts
    """

    today = date.today()
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid deadline format. Use YYYY-MM-DD."}

    days_left = (deadline - today).days

    # ── Edge cases ──────────────────────────────────────────────────────────
    alerts = []
    if days_left < 0:
        return {
            "task_name": task_name,
            "risk_level": "CRITICAL",
            "miss_probability": 100,
            "days_left": days_left,
            "available_hours": 0,
            "adjusted_hours": round(estimated_hours, 2),
            "recommended_daily_hours": None,
            "schedule_advice": "Deadline has already passed.",
            "alerts": ["Deadline has already passed!"],
        }

    if days_left == 0:
        alerts.append("Deadline is today!")

    # ── Core calculation ─────────────────────────────────────────────────────
    WORKING_HOURS_PER_DAY = 8.0
    effective_daily = max(WORKING_HOURS_PER_DAY - daily_workload, 0.5)
    available_hours = effective_daily * days_left

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
    if daily_workload >= WORKING_HOURS_PER_DAY:
        alerts.append("Your current workload already fills a full workday — no buffer left.")
    if past_speed < 60:
        alerts.append("Historical completion rate below 60 % — consider revising your estimate.")
    if days_left <= 2 and miss_probability > 50:
        alerts.append("Very little time remaining. Consider negotiating the deadline.")

    # Recommended daily hours to finish on time
    if days_left > 0:
        recommended_daily = math.ceil((adjusted_hours / days_left) * 10) / 10
    else:
        recommended_daily = None

    schedule_advice = _build_advice(ratio, recommended_daily, daily_workload, past_speed)

    return {
        "task_name": task_name,
        "risk_level": risk_level,
        "miss_probability": round(miss_probability, 1),
        "days_left": days_left,
        "available_hours": round(available_hours, 2),
        "adjusted_hours": round(adjusted_hours, 2),
        "recommended_daily_hours": recommended_daily,
        "schedule_advice": schedule_advice,
        "alerts": alerts,
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
