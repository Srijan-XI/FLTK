import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def test_total_base_computed_on_create(temp_data_dir):
    cfg = dict(h.DEFAULT_SETTINGS)
    cfg["currency"] = "INR"
    cfg["currency_symbol"] = "₹"
    h.save_settings(cfg)

    inv = h.create_invoice(
        client_name="Acme",
        items=[{"description": "Dev", "hours": 2, "rate": 100}],
        due_date="2099-12-31",
        currency="USD",
        currency_symbol="$",
        exchange_rate=80.0,
        base_currency="INR",
    )

    assert inv["total"] == 200.0
    assert inv["total_base"] == 16000.0
    assert inv["base_currency"] == "INR"


def test_earnings_summary_uses_base_currency(temp_data_dir):
    cfg = dict(h.DEFAULT_SETTINGS)
    cfg["currency"] = "INR"
    cfg["currency_symbol"] = "₹"
    h.save_settings(cfg)

    inv = h.create_invoice(
        client_name="Beta",
        items=[{"description": "Consulting", "hours": 1, "rate": 100}],
        due_date="2099-12-31",
        currency="USD",
        currency_symbol="$",
        exchange_rate=75.0,
        base_currency="INR",
    )
    h.mark_invoice_paid(inv["id"])

    summary = h.get_earnings_summary()
    assert summary["total_paid"] == 7500.0


def test_existing_invoices_default_to_rate_1(temp_data_dir):
    cfg = dict(h.DEFAULT_SETTINGS)
    cfg["currency"] = "USD"
    cfg["currency_symbol"] = "$"
    h.save_settings(cfg)

    h._save(
        "invoices.json",
        [
            {
                "id": 1,
                "invoice_number": "INV-0001",
                "client_name": "Legacy",
                "issue_date": "2026-03-01",
                "due_date": "2026-03-31",
                "items": [],
                "subtotal": 100.0,
                "tax_rate": 0.0,
                "tax_amount": 0.0,
                "total": 100.0,
                "currency": "USD",
                "currency_symbol": "$",
                "status": "paid",
                "notes": "",
            }
        ],
    )

    summary = h.get_earnings_summary()
    assert summary["total_paid"] == 100.0
