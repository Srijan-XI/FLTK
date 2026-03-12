import pytest

from app import app
from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    h.save_settings(h.DEFAULT_SETTINGS)
    return tmp_path


def test_calendar_events_includes_project_dates(temp_data_dir):
    client = h.add_client(name="Acme", email="acme@example.com")
    template = h.get_sdlc_templates()[0]
    h.add_scoped_project(
        client_id=client["id"],
        template_id=template["id"],
        project_name="Portal Build",
        start_date="2026-03-10",
        target_date="2026-03-15",
    )

    events = h.get_calendar_events(2026, 3)

    assert "Portal Build" in events["2026-03-12"]["projects"]


def test_calendar_events_sums_hours_per_day(temp_data_dir):
    h.log_hours(task="Build", client="Acme", hours=2.5, log_date="2026-03-08")
    h.log_hours(task="Review", client="Acme", hours=1.5, log_date="2026-03-08")

    events = h.get_calendar_events(2026, 3)

    assert events["2026-03-08"]["hours"] == 4.0


def test_block_marks_day_as_blocked(temp_data_dir):
    h.add_calendar_block("2026-03-18", "2026-03-18", "Vacation", "vacation")

    events = h.get_calendar_events(2026, 3)

    assert events["2026-03-18"]["status"] == "blocked"


def test_api_endpoint_returns_json(temp_data_dir):
    client = app.test_client()

    resp = client.get("/wft/calendar/api/events?year=2026&month=3")

    assert resp.status_code == 200
    assert resp.is_json
    payload = resp.get_json()
    assert "2026-03-01" in payload
