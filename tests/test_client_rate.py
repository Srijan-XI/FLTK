import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def test_get_rate_at_date_before_any_history_uses_default(temp_data_dir):
    client = h.add_client(name="Acme", email="acme@example.com", default_rate=40.0)

    rate = h.get_client_rate_at(client["id"], "2024-01-01")
    assert rate == 40.0


def test_get_rate_at_date_returns_correct_historical_entry(temp_data_dir):
    client = h.add_client(name="Beta", email="beta@example.com", default_rate=35.0)
    h.add_client_rate_entry(client["id"], 50.0, "2025-01-01", "Annual increase")
    h.add_client_rate_entry(client["id"], 60.0, "2025-07-01", "Mid-year increase")

    assert h.get_client_rate_at(client["id"], "2025-03-15") == 50.0
    assert h.get_client_rate_at(client["id"], "2025-10-01") == 60.0


def test_add_rate_entry_keeps_list_sorted(temp_data_dir):
    client = h.add_client(name="Gamma", email="gamma@example.com", default_rate=45.0)
    h.add_client_rate_entry(client["id"], 55.0, "2025-09-01", "Later entry")
    h.add_client_rate_entry(client["id"], 50.0, "2025-02-01", "Earlier entry")

    refreshed = h.get_client(client["id"])
    history = refreshed.get("rate_history", [])
    assert [e["from"] for e in history] == ["2025-02-01", "2025-09-01"]
