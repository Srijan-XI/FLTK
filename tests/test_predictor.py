"""
Unit tests for modules/drp/predictor.py
Run with: pytest tests/test_predictor.py -v
"""
import pytest
from modules.drp.predictor import predict, _ratio_to_probability, _probability_to_risk


class TestRatioToProbability:
    def test_very_safe_returns_low_probability(self):
        p = _ratio_to_probability(3.0)
        assert p <= 10, f"ratio=3 should give low probability, got {p}"

    def test_slightly_over_returns_moderate(self):
        p = _ratio_to_probability(1.0)
        assert 40 <= p <= 60, f"ratio=1 should give ~50%, got {p}"

    def test_overloaded_returns_high(self):
        p = _ratio_to_probability(0.2)
        assert p >= 80, f"ratio=0.2 should give high probability, got {p}"

    def test_infinite_ratio_returns_minimum(self):
        p = _ratio_to_probability(float("inf"))
        assert p <= 5

    def test_probability_is_smooth_no_big_jumps(self):
        """Adjacent ratios should not jump more than 20 percentage points."""
        ratios = [2.0, 1.5, 1.25, 1.0, 0.8, 0.6, 0.4]
        probs  = [_ratio_to_probability(r) for r in ratios]
        for a, b in zip(probs, probs[1:]):
            assert abs(b - a) <= 25, f"Probability jump too large: {a} → {b}"

    def test_clamped_to_3_97(self):
        for ratio in [100.0, 0.0]:
            p = _ratio_to_probability(ratio)
            assert 3.0 <= p <= 97.0


class TestProbabilityToRisk:
    def test_low(self):      assert _probability_to_risk(10) == "LOW"
    def test_medium(self):   assert _probability_to_risk(45) == "MEDIUM"
    def test_high(self):     assert _probability_to_risk(65) == "HIGH"
    def test_critical(self): assert _probability_to_risk(80) == "CRITICAL"


class TestPredict:
    def test_past_deadline_returns_critical(self):
        result = predict("Test", 10, "2020-01-01", 80, 0)
        assert result["risk_level"] == "CRITICAL"
        assert result["miss_probability"] == 100
        assert "passed" in result["schedule_advice"].lower()

    def test_invalid_date_returns_error(self):
        result = predict("Test", 10, "not-a-date", 80, 0)
        assert "error" in result

    def test_comfortable_schedule_is_low_risk(self):
        # 5 estimated hours, 60 days left, 100% speed, 0 workload
        result = predict("Easy", 5, "2026-04-30", 100, 0)
        assert result["risk_level"] in ("LOW", "MEDIUM")
        assert result["miss_probability"] < 50

    def test_overloaded_schedule_is_high_risk(self):
        # 100 hours needed, deadline tomorrow, 50% speed, 6h daily workload
        import datetime
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        result = predict("Crunch", 100, tomorrow, 50, 6)
        assert result["risk_level"] in ("HIGH", "CRITICAL")
        assert result["miss_probability"] > 60

    def test_result_keys_present(self):
        import datetime
        future = (datetime.date.today() + datetime.timedelta(days=14)).isoformat()
        result = predict("Task", 20, future, 70, 2)
        expected_keys = ["task_name", "risk_level", "miss_probability",
                         "days_left", "available_hours", "adjusted_hours",
                         "recommended_daily_hours", "schedule_advice", "alerts"]
        for k in expected_keys:
            assert k in result, f"Missing key: {k}"

    def test_deadline_today_shows_alert(self):
        import datetime
        today = datetime.date.today().isoformat()
        result = predict("Task", 4, today, 70, 0)
        assert any("today" in a.lower() for a in result["alerts"])

    def test_poor_speed_triggers_alert(self):
        import datetime
        future = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        result = predict("Task", 20, future, 40, 0)
        assert any("60" in a for a in result["alerts"])

    def test_heavy_workload_triggers_alert(self):
        import datetime
        future = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        result = predict("Task", 20, future, 70, 8)
        assert any("workload" in a.lower() or "full workday" in a.lower()
                   for a in result["alerts"])
