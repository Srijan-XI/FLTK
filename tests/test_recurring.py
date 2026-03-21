from datetime import date

import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def _set_recurring(inv_id: int, interval: str, last_generated: str):
    invoices = h._load("invoices.json")
    for inv in invoices:
        if inv.get("id") == inv_id:
            inv["recurring"] = True
            inv["recur_interval"] = interval
            inv["last_generated"] = last_generated
            break
    h._save("invoices.json", invoices)


def test_due_monthly_invoice_detected(temp_data_dir):
    inv = h.create_invoice("Acme", [{"description": "Retainer", "hours": 1, "rate": 500}], "2099-12-31")
    _set_recurring(inv["id"], "monthly", "2000-01-01")

    due = h.get_due_recurring_invoices()
    assert any(i["id"] == inv["id"] for i in due)


def test_not_due_if_generated_this_month(temp_data_dir):
    today = date.today().isoformat()
    inv = h.create_invoice("Acme", [{"description": "Retainer", "hours": 1, "rate": 500}], "2099-12-31")
    _set_recurring(inv["id"], "monthly", today)

    due = h.get_due_recurring_invoices()
    assert all(i["id"] != inv["id"] for i in due)


def test_generate_creates_new_invoice_with_correct_dates(temp_data_dir):
    inv = h.create_invoice("Acme", [{"description": "Retainer", "hours": 2, "rate": 100}], "2099-12-31")
    h.set_invoice_recurring_interval(inv["id"], "monthly")

    invoices = h._load("invoices.json")
    for item in invoices:
        if item["id"] == inv["id"]:
            item["issue_date"] = "2026-01-01"
            item["due_date"] = "2026-01-31"
            item["last_generated"] = "2000-01-01"
    h._save("invoices.json", invoices)

    generated = h.generate_recurring_invoice(inv["id"])
    assert generated["source_recurring_id"] == inv["id"]
    assert generated["status"] == "unpaid"
    assert generated["due_date"] >= generated["issue_date"]


def test_generate_updates_last_generated_on_source(temp_data_dir):
    inv = h.create_invoice("Acme", [{"description": "Retainer", "hours": 1, "rate": 100}], "2099-12-31")
    h.set_invoice_recurring_interval(inv["id"], "monthly")

    generated = h.generate_recurring_invoice(inv["id"])
    source = next(i for i in h.get_invoices() if i["id"] == inv["id"])

    assert generated["id"] != inv["id"]
    assert source.get("last_generated") == date.today().isoformat()


def test_generate_all_due_returns_correct_count(temp_data_dir):
    first = h.create_invoice("Acme", [{"description": "R1", "hours": 1, "rate": 100}], "2099-12-31")
    second = h.create_invoice("Beta", [{"description": "R2", "hours": 1, "rate": 120}], "2099-12-31")
    _set_recurring(first["id"], "monthly", "2000-01-01")
    _set_recurring(second["id"], "monthly", "2000-01-01")

    created = h.generate_all_due_recurring()
    assert len(created) == 2


def test_toggle_recurring_flag(temp_data_dir):
    inv = h.create_invoice("Acme", [{"description": "Retainer", "hours": 1, "rate": 100}], "2099-12-31")

    enabled = h.toggle_invoice_recurring(inv["id"])
    assert enabled["recurring"] is True

    disabled = h.toggle_invoice_recurring(inv["id"])
    assert disabled["recurring"] is False
