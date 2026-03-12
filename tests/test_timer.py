from datetime import datetime, timedelta

import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def test_start_timer_creates_running_session(temp_data_dir):
    session = h.start_timer(client="Acme", task="Homepage", mode="normal")

    assert session["status"] == "running"
    assert session["client"] == "Acme"
    assert h.get_active_session() is not None


def test_cannot_start_two_sessions(temp_data_dir):
    h.start_timer(client="Acme", task="Task A", mode="normal")

    with pytest.raises(ValueError):
        h.start_timer(client="Beta", task="Task B", mode="normal")


def test_stop_timer_calculates_duration(temp_data_dir):
    session = h.start_timer(client="Acme", task="Deep Work", mode="normal")

    sessions = h._load(h.TIMER_FILE)
    sessions[0]["start_time"] = (datetime.now().replace(microsecond=0) - timedelta(hours=1)).isoformat()
    h._save(h.TIMER_FILE, sessions)

    stopped = h.stop_timer(session["id"])

    assert stopped["status"] == "stopped"
    assert stopped["duration_seconds"] >= 3599


def test_save_to_hours_creates_workhour_entry(temp_data_dir):
    session = h.start_timer(client="Acme", task="API Integration", mode="normal")

    sessions = h._load(h.TIMER_FILE)
    sessions[0]["start_time"] = (datetime.now().replace(microsecond=0) - timedelta(minutes=30)).isoformat()
    h._save(h.TIMER_FILE, sessions)
    h.stop_timer(session["id"])

    saved = h.save_timer_to_hours(session["id"])
    entries = h.get_workhours()

    assert saved["status"] == "saved"
    assert len(entries) == 1
    assert entries[0]["task"] == "API Integration"


def test_discard_does_not_save_hours(temp_data_dir):
    session = h.start_timer(client="Acme", task="Research", mode="pomodoro")

    sessions = h._load(h.TIMER_FILE)
    sessions[0]["start_time"] = (datetime.now().replace(microsecond=0) - timedelta(minutes=10)).isoformat()
    h._save(h.TIMER_FILE, sessions)
    h.stop_timer(session["id"])
    h.discard_timer(session["id"])

    entries = h.get_workhours()
    discarded = h.get_timer_sessions()[0]

    assert entries == []
    assert discarded["status"] == "discarded"
