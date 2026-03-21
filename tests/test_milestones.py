from datetime import date, timedelta

import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def _seed_project(total_value: float = 1000.0):
    client = h.add_client(name="Acme", email="acme@example.com")
    template = h.get_sdlc_templates()[0]
    return h.add_scoped_project(
        client_id=client["id"],
        template_id=template["id"],
        project_name="Acme Website",
        summary="Milestone-enabled project",
        total_value=total_value,
    )


def test_add_milestone_computes_amount_from_project_total(temp_data_dir):
    project = _seed_project(total_value=2000.0)
    ms = h.add_milestone(project["id"], "Design", "2099-01-15", 25, "")

    assert ms["amount"] == 500.0


def test_milestone_percent_validation_rejects_over_100(temp_data_dir):
    project = _seed_project(total_value=1000.0)
    h.add_milestone(project["id"], "Phase 1", "2099-01-10", 70, "")

    with pytest.raises(ValueError):
        h.add_milestone(project["id"], "Phase 2", "2099-01-20", 40, "")


def test_create_invoice_from_milestone_sets_invoice_id(temp_data_dir):
    project = _seed_project(total_value=1500.0)
    ms = h.add_milestone(project["id"], "Build", "2099-02-01", 40, "")

    invoice = h.create_invoice_from_milestone(ms["id"])
    reloaded = h.get_milestone(ms["id"])

    assert invoice["invoice_number"].startswith("INV-")
    assert reloaded is not None
    assert reloaded["invoice_id"] == invoice["id"]
    assert reloaded["status"] == "invoiced"


def test_delete_only_allowed_on_pending_milestone(temp_data_dir):
    project = _seed_project(total_value=1000.0)
    pending = h.add_milestone(project["id"], "Pending", "2099-03-01", 20, "")
    delivered = h.add_milestone(project["id"], "Delivered", "2099-03-05", 20, "")
    h.update_milestone_status(delivered["id"], "delivered")

    assert h.delete_milestone(pending["id"]) is True
    assert h.delete_milestone(delivered["id"]) is False


def test_get_upcoming_milestones_filters_by_days(temp_data_dir):
    project = _seed_project(total_value=1000.0)
    soon = (date.today() + timedelta(days=7)).isoformat()
    later = (date.today() + timedelta(days=30)).isoformat()

    near_ms = h.add_milestone(project["id"], "Soon", soon, 10, "")
    h.add_milestone(project["id"], "Later", later, 10, "")

    upcoming = h.get_upcoming_milestones(days=14)
    assert any(ms["id"] == near_ms["id"] for ms in upcoming)
    assert all(ms["due_date"] <= (date.today() + timedelta(days=14)).isoformat() for ms in upcoming)
