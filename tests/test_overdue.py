import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def test_overdue_detection_by_date(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    h.create_invoice(
        client_name="Acme",
        items=[{"description": "Build", "hours": 2, "rate": 100}],
        due_date="2000-01-01",
    )

    overdue = h.get_overdue_invoices()
    assert len(overdue) == 1
    assert overdue[0]["client_name"] == "Acme"


def test_days_overdue_calculation(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    h.create_invoice(
        client_name="Beta",
        items=[{"description": "Work", "hours": 1, "rate": 120}],
        due_date="2000-01-10",
    )

    overdue = h.get_overdue_invoices()
    assert overdue[0]["days_overdue"] > 0


def test_late_fee_calculation(temp_data_dir):
    cfg = dict(h.DEFAULT_SETTINGS)
    cfg["late_fee_rate"] = 3.0
    h.save_settings(cfg)
    inv = h.create_invoice(
        client_name="Gamma",
        items=[{"description": "Task", "hours": 10, "rate": 50}],
        due_date="2000-01-01",
    )

    overdue = h.get_overdue_invoices()
    item = next(row for row in overdue if row["id"] == inv["id"])
    assert item["late_fee_amount"] > 0


def test_reminder_email_contains_key_fields(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    inv = h.create_invoice(
        client_name="Delta",
        items=[{"description": "Task", "hours": 4, "rate": 75}],
        due_date="2000-01-01",
    )
    overdue = h.get_overdue_invoices()
    enriched = next(row for row in overdue if row["id"] == inv["id"])

    draft = h.get_reminder_email_draft(enriched)
    assert inv["invoice_number"] in draft
    assert "Delta" in draft
    assert "Subject:" in draft
