import pytest
from flask import render_template

from app import app
from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def test_create_contract_auto_fills_freelancer_info(temp_data_dir):
    cfg = dict(h.DEFAULT_SETTINGS)
    cfg["name"] = "Alex Freelancer"
    cfg["business"] = "Alex Labs"
    h.save_settings(cfg)

    client = h.add_client(name="Acme Corp", email="hello@acme.test")
    contract = h.add_contract(
        title="Web App Contract - Acme",
        contract_type="Service Agreement",
        client_id=client["id"],
        project_description="Build an internal dashboard",
    )

    assert contract["freelancer_name"] == "Alex Freelancer"
    assert contract["freelancer_business"] == "Alex Labs"
    assert contract["client_name"] == "Acme Corp"


def test_contract_status_progression(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    contract = h.add_contract(
        title="NDA - Delta",
        contract_type="Non-Disclosure Agreement (NDA)",
    )

    h.update_contract(contract["id"], status="sent")
    h.update_contract(contract["id"], status="signed")

    updated = h.get_contract(contract["id"])
    assert updated is not None
    assert updated["status"] == "signed"


def test_contract_pdf_renders_without_error(temp_data_dir):
    h.save_settings(h.DEFAULT_SETTINGS)
    contract = h.add_contract(
        title="Retainer Contract",
        contract_type="Retainer Agreement",
        client_name="Example Client",
    )

    with app.test_request_context():
        html = render_template("wft/contracts/contract_print.html", contract=contract)

    assert "Retainer Contract" in html
    assert "Example Client" in html
