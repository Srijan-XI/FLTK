import io
import os

import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    h.save_settings(h.DEFAULT_SETTINGS)
    return tmp_path


def test_import_preview_and_commit_clients(temp_data_dir):
    csv_bytes = b"name,email,phone\nAcme,acme@example.com,12345\n"

    preview, errs = h.import_preview("clients", "clients.csv", csv_bytes)

    assert not errs
    assert len(preview) == 1
    created = h.import_commit("clients", preview)
    assert created == 1
    assert len(h.get_clients()) == 1


def test_recurring_reminders_detect_t_offsets(temp_data_dir):
    inv = h.create_invoice(
        client_name="Beta",
        items=[{"description": "Support", "hours": 1, "rate": 100}],
        due_date=(h.date.today() + h.timedelta(days=3)).isoformat(),
    )

    reminders = h.recurring_reminders(offsets=[3])

    assert any(r["invoice_id"] == inv["id"] and r["label"] == "T-3" for r in reminders)


def test_saved_invoice_views_and_filtering(temp_data_dir):
    h.create_invoice("Acme", [{"description": "A", "hours": 1, "rate": 100}], due_date="2026-04-01")
    h.create_invoice("Beta", [{"description": "B", "hours": 1, "rate": 100}], due_date="2026-04-01")

    h.save_invoice_view("AcmeOnly", {"client": "Acme", "status": "", "start_date": "", "end_date": ""})
    views = h.get_invoice_saved_views()

    assert any(v["name"] == "AcmeOnly" for v in views)
    filtered = h.filter_invoices(h.get_invoices(), {"client": "Acme", "status": "", "start_date": "", "end_date": ""})
    assert len(filtered) == 1
    assert filtered[0]["client_name"] == "Acme"


def test_bulk_invoice_actions(temp_data_dir):
    a = h.create_invoice("Acme", [{"description": "A", "hours": 1, "rate": 100}], due_date="2026-04-01")
    b = h.create_invoice("Beta", [{"description": "B", "hours": 1, "rate": 200}], due_date="2026-04-01")

    changed = h.bulk_invoice_action([a["id"], b["id"]], "mark_paid")
    assert changed == 2
    assert all(i["payment_status"] == "paid" for i in h.get_invoices())

    csv_text = h.invoice_ids_to_csv([a["id"], b["id"]])
    assert "Invoice #" in csv_text


def test_local_attachments_for_entities(temp_data_dir):
    inv = h.create_invoice("Acme", [{"description": "A", "hours": 1, "rate": 100}], due_date="2026-04-01")

    att = h.add_attachment("invoice", inv["id"], "spec.txt", b"hello")
    listed = h.list_attachments("invoice", inv["id"])

    assert len(listed) == 1
    assert listed[0]["id"] == att["id"]

    on_disk = os.path.join(str(temp_data_dir), "attachments", att["stored_name"])
    assert os.path.exists(on_disk)

    assert h.delete_attachment(att["id"])
    assert h.list_attachments("invoice", inv["id"]) == []
