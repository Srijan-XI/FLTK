import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def _seed_data():
    h.create_invoice(
        client_name="Acme",
        items=[{"description": "Dev", "hours": 5, "rate": 100}],
        due_date="2099-12-31",
    )
    h.create_invoice(
        client_name="Beta",
        items=[{"description": "Design", "hours": 2, "rate": 150}],
        due_date="2099-12-31",
    )
    h.mark_invoice_paid(1)
    h.mark_invoice_paid(2)
    h.log_hours(task="Dev", client="Acme", hours=5, log_date="2026-03-01")
    h.log_hours(task="Design", client="Beta", hours=2, log_date="2026-03-08")
    h.add_expense(title="Tooling", amount=50, category="Software & Tools", expense_date="2026-03-02")


def test_income_by_month_last_12(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    _seed_data()
    summary = h.get_earnings_summary()

    assert len(summary["income_by_month"]) <= 12
    assert sum(summary["income_by_month"].values()) > 0


def test_income_by_client_top_10(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    _seed_data()
    summary = h.get_earnings_summary()

    assert len(summary["income_by_client"]) <= 10
    assert "Acme" in summary["income_by_client"]


def test_weekly_hours_last_12_weeks(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    _seed_data()
    summary = h.get_earnings_summary()

    assert len(summary["weekly_hours"]) <= 12
    assert all("week" in row and "hours" in row for row in summary["weekly_hours"])


def test_expense_by_category(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    _seed_data()
    summary = h.get_earnings_summary()

    assert summary["expense_by_cat"]["Software & Tools"] == 50


def test_profit_by_month(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    _seed_data()
    summary = h.get_earnings_summary()

    assert len(summary["profit_by_month"]) <= 12
    assert any(value >= 0 for value in summary["profit_by_month"].values())
