import pytest

from app import app
from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    h.save_settings(h.DEFAULT_SETTINGS)
    return tmp_path


def test_sitemap_page_lists_paths(temp_data_dir):
    client = app.test_client()

    response = client.get("/wft/sitemap")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "/wft/sitemap" in body
    assert "/wft/clients" in body
    assert "/drp/" in body
