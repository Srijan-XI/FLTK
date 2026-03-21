import json
import os

import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    h.save_settings(h.DEFAULT_SETTINGS)
    return tmp_path


def test_restore_point_can_roll_back_clients(temp_data_dir):
    h.add_client(name="Acme", email="acme@example.com")
    point = h.create_restore_point(label="before-second-client")

    h.add_client(name="Beta", email="beta@example.com")
    assert len(h.get_clients()) == 2

    restored, errors = h.restore_restore_point(point["filename"])

    assert not errors
    assert "clients.json" in restored
    clients = h.get_clients()
    assert len(clients) == 1
    assert clients[0]["name"] == "Acme"


def test_integrity_repair_removes_orphan_milestone(temp_data_dir):
    projects_path = os.path.join(str(temp_data_dir), h.SCOPED_PROJECT_FILE)
    milestones_path = os.path.join(str(temp_data_dir), h.MILESTONE_FILE)

    with open(projects_path, "w", encoding="utf-8") as f:
        json.dump([], f)
    with open(milestones_path, "w", encoding="utf-8") as f:
        json.dump([
            {"id": 1, "project_id": 99, "name": "Ghost", "due_date": "2026-03-30", "status": "pending"}
        ], f)

    report = h.scan_data_integrity(auto_repair=False)
    assert any(issue["code"] == "orphan_milestone" for issue in report["issues"])

    repaired = h.scan_data_integrity(auto_repair=True)
    assert any("orphan milestone" in item.lower() for item in repaired["repairs"])

    with open(milestones_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == []
