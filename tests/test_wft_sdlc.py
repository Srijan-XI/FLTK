import pathlib

import pytest

from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    return tmp_path


def test_sdlc_templates_bootstrap_defaults(temp_data_dir):
    templates = h.get_sdlc_templates()

    assert len(templates) == 9
    assert any(template["name"] == "Agile Model" for template in templates)
    assert pathlib.Path(temp_data_dir, h.SDLC_TEMPLATE_FILE).exists()


def test_add_custom_sdlc_template_persists(temp_data_dir):
    template = h.add_sdlc_template(
        name="Discovery Sprint",
        summary="A short discovery-first model",
        best_for="Workshops and validation",
        phases="Discovery\nPrototype\nScope Freeze",
        deliverables="Workshop notes\nPrototype",
        tags="discovery, workshop",
    )

    reloaded = h.get_sdlc_template(template["id"])
    assert reloaded is not None
    assert reloaded["name"] == "Discovery Sprint"
    assert reloaded["phases"] == ["Discovery", "Prototype", "Scope Freeze"]
    assert reloaded["tags"] == ["discovery", "workshop"]


def test_scoped_project_links_client_and_template(temp_data_dir):
    client = h.add_client(name="Acme", email="hello@acme.test")
    template = h.get_sdlc_templates()[0]

    project = h.add_scoped_project(
        client_id=client["id"],
        template_id=template["id"],
        project_name="Acme Portal",
        summary="Client portal scope",
        objectives="Launch MVP\nProtect scope",
        scope_in="Dashboard\nLogin",
        scope_out="Native apps",
        deliverables="Wireframes\nBuild\nQA",
        milestones="Planning\nDelivery",
        change_control="All changes require approval.",
        revision_policy="Two revision rounds.",
        acceptance_criteria="Deployed build\nClient sign-off",
        status="active",
    )

    fetched = h.get_scoped_project(project["id"])
    assert fetched is not None
    assert fetched["client_name"] == "Acme"
    assert fetched["template_name"] == template["name"]
    assert fetched["scope_out"] == ["Native apps"]
    assert fetched["status"] == "active"


def test_global_search_finds_sdlc_templates_and_projects(temp_data_dir):
    client = h.add_client(name="Northwind", email="team@northwind.test")
    template = h.add_sdlc_template(
        name="Northwind Validation Model",
        summary="Unique validation workflow",
        best_for="Unique pilot",
        phases="Assess\nBuild",
    )
    h.add_scoped_project(
        client_id=client["id"],
        template_id=template["id"],
        project_name="Northwind Pilot",
        summary="Unique rollout scope",
    )

    results = h.global_search("northwind")

    assert len(results["clients"]) == 1
    assert len(results["sdlc_templates"]) == 1
    assert len(results["scoped_projects"]) == 1
    assert results["scoped_projects"][0]["project_name"] == "Northwind Pilot"
