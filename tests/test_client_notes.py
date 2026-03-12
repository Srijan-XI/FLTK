import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def _seed_client():
    return h.add_client(name="Acme", email="acme@example.com")


def test_add_note_to_client(temp_data_dir):
    client = _seed_client()
    note = h.add_client_note(client["id"], "Kickoff", "Discussed roadmap")

    notes = h.get_client_notes(client["id"])
    assert len(notes) == 1
    assert notes[0]["id"] == note["id"]


def test_pinned_notes_appear_first(temp_data_dir):
    client = _seed_client()
    first = h.add_client_note(client["id"], "General", "General details")
    second = h.add_client_note(client["id"], "Priority", "Important details")

    h.toggle_note_pin(second["id"])
    notes = h.get_client_notes(client["id"])

    assert notes[0]["id"] == second["id"]
    assert notes[1]["id"] == first["id"]


def test_toggle_pin(temp_data_dir):
    client = _seed_client()
    note = h.add_client_note(client["id"], "Follow up", "Call next week")

    before = h.get_client_note(note["id"])
    assert before["pinned"] is False

    h.toggle_note_pin(note["id"])
    after = h.get_client_note(note["id"])
    assert after["pinned"] is True


def test_search_finds_notes_by_content(temp_data_dir):
    client = _seed_client()
    h.add_client_note(client["id"], "Call", "Client asked about payment schedule")

    results = h.search_client_notes("payment schedule")
    assert len(results) == 1
    assert results[0]["client_id"] == client["id"]
