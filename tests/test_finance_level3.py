import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    h.save_settings(h.DEFAULT_SETTINGS)
    return tmp_path


def test_partial_payment_and_ledger(temp_data_dir):
    inv = h.create_invoice(
        client_name="Acme",
        items=[{"description": "Build", "hours": 10, "rate": 100}],
        due_date="2026-03-30",
    )

    inv = h.add_invoice_payment(inv["id"], amount=300, note="Advance")
    inv = h.add_invoice_adjustment(inv["id"], amount=-50, reason="Discount")

    assert inv["payment_status"] == "partial"
    assert inv["adjusted_total"] == 950.0
    assert inv["total_paid"] == 300.0
    assert inv["balance_due"] == 650.0

    ledger = h.get_invoice_ledger(inv["id"])
    assert len(ledger) >= 3
    assert ledger[-1]["running_balance"] == 650.0


def test_cashflow_forecast_includes_unpaid_invoice(temp_data_dir):
    h.create_invoice(
        client_name="Beta",
        items=[{"description": "Retainer", "hours": 5, "rate": 200}],
        due_date="2026-04-01",
    )

    forecast = h.cashflow_forecast(days=120)

    assert forecast["totals"]["best"] >= forecast["totals"]["likely"] >= forecast["totals"]["worst"]
    assert any(item["type"] == "invoice" for item in forecast["items"])


def test_margin_intelligence_alerts_below_target(temp_data_dir):
    h.log_hours(task="Dev", client="Gamma", hours=20, log_date="2026-03-10")
    inv = h.create_invoice(
        client_name="Gamma",
        items=[{"description": "Dev", "hours": 20, "rate": 20}],
        due_date="2026-03-20",
    )
    h.mark_invoice_paid(inv["id"])

    report = h.margin_intelligence(target_rate=50)

    assert any(alert["client"] == "Gamma" for alert in report["alerts"])


def test_change_order_can_apply_invoice_delta(temp_data_dir):
    inv = h.create_invoice(
        client_name="Delta",
        items=[{"description": "Sprint", "hours": 4, "rate": 100}],
        due_date="2026-03-25",
    )
    order = h.add_change_order(
        client_name="Delta",
        description="Extra revision round",
        amount_delta=120,
        hours_delta=2,
        invoice_id=inv["id"],
        status="submitted",
    )

    updated = h.update_change_order_status(order["id"], status="approved", apply_to_invoice=True)
    enriched = h.get_invoice(inv["id"])

    assert updated["status"] == "invoiced"
    assert enriched is not None
    assert enriched["adjusted_total"] == 520.0


def test_ar_risk_scoring_ranks_overdue_higher(temp_data_dir):
    high = h.create_invoice(
        client_name="LateCo",
        items=[{"description": "Project", "hours": 10, "rate": 100}],
        due_date="2026-01-01",
    )
    low = h.create_invoice(
        client_name="FreshCo",
        items=[{"description": "Support", "hours": 2, "rate": 100}],
        due_date="2099-01-01",
    )

    scores = h.get_ar_risk_scores()
    by_id = {row["invoice_id"]: row for row in scores}

    assert by_id[high["id"]]["risk_score"] >= by_id[low["id"]]["risk_score"]
