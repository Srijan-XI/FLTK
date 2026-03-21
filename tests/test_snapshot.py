from datetime import date

import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def _set_invoice_issue_date(invoice_id: int, issue_date: str):
    invoices = h._load("invoices.json")
    for inv in invoices:
        if inv.get("id") == invoice_id:
            inv["issue_date"] = issue_date
            break
    h._save("invoices.json", invoices)


def test_ytd_income_sums_paid_invoices_current_year(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    current_year = date.today().year

    inv1 = h.create_invoice("Acme", [{"description": "A", "hours": 1, "rate": 100}], "2099-12-31")
    inv2 = h.create_invoice("Beta", [{"description": "B", "hours": 2, "rate": 100}], "2099-12-31")
    old_inv = h.create_invoice("Legacy", [{"description": "Old", "hours": 5, "rate": 100}], "2099-12-31")

    h.mark_invoice_paid(inv1["id"])
    h.mark_invoice_paid(inv2["id"])
    h.mark_invoice_paid(old_inv["id"])

    _set_invoice_issue_date(inv1["id"], f"{current_year}-01-10")
    _set_invoice_issue_date(inv2["id"], f"{current_year}-02-15")
    _set_invoice_issue_date(old_inv["id"], f"{current_year - 1}-12-20")

    snap = h.get_financial_snapshot()
    assert snap["ytd_income"] == 300.0


def test_ytd_expenses_sums_this_year(temp_data_dir):
    current_year = date.today().year

    h.add_expense("Hosting", 60.0, expense_date=f"{current_year}-01-05")
    h.add_expense("Travel", 40.0, expense_date=f"{current_year}-02-05")
    h.add_expense("Legacy", 100.0, expense_date=f"{current_year - 1}-11-05")

    snap = h.get_financial_snapshot()
    assert snap["ytd_expenses"] == 100.0


def test_effective_hourly_divides_by_hours(temp_data_dir):
    current_year = date.today().year

    inv = h.create_invoice("Acme", [{"description": "Dev", "hours": 3, "rate": 100}], "2099-12-31")
    h.mark_invoice_paid(inv["id"])
    _set_invoice_issue_date(inv["id"], f"{current_year}-03-01")

    h.log_hours("Task 1", "Acme", 2.0, log_date=f"{current_year}-03-02")
    h.log_hours("Task 2", "Acme", 1.0, log_date=f"{current_year}-03-03")

    snap = h.get_financial_snapshot()
    assert snap["effective_hourly"] == 100.0


def test_net_is_income_minus_expenses(temp_data_dir):
    current_year = date.today().year

    inv = h.create_invoice("Acme", [{"description": "Work", "hours": 2, "rate": 100}], "2099-12-31")
    h.mark_invoice_paid(inv["id"])
    _set_invoice_issue_date(inv["id"], f"{current_year}-04-05")

    h.add_expense("Software", 30.0, expense_date=f"{current_year}-04-06")

    snap = h.get_financial_snapshot()
    assert snap["ytd_net"] == 170.0
