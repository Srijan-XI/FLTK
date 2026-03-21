import datetime

import pytest

from app import app
from modules.drp import history as drp_hist
from modules.drp.predictor import predict
from modules.wft import helpers as h


@pytest.fixture()
def temp_data_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(h, "SETTINGS_FILE", str(tmp_path / "settings.json"))
    monkeypatch.setattr(drp_hist, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(drp_hist, "HISTORY_FILE", str(tmp_path / "drp_history.json"))

    h.save_settings(h.DEFAULT_SETTINGS)
    app.config["TESTING"] = True
    return tmp_path


def test_predict_calendar_aware_availability(temp_data_dirs):
    today = datetime.date.today()
    deadline = (today + datetime.timedelta(days=4)).isoformat()
    blocked = {(today + datetime.timedelta(days=1)).isoformat()}

    result = predict(
        task_name="Calendar Aware",
        estimated_hours=8,
        deadline_str=deadline,
        past_speed=100,
        daily_workload=0,
        working_hours_per_day=8,
        include_weekends=True,
        unavailable_dates=blocked,
    )

    assert "error" not in result
    assert result["available_days"] == 3
    assert result["calendar_summary"]["blocked_days"] == 1


def test_drp_wft_context_linking_and_report_route(temp_data_dirs):
    client = h.add_client(name="Acme", email="acme@test.local")
    template = h.get_sdlc_templates()[0]
    project = h.add_scoped_project(
        client_id=client["id"],
        template_id=template["id"],
        project_name="Portal",
        target_date=(datetime.date.today() + datetime.timedelta(days=14)).isoformat(),
    )
    milestone = h.add_milestone(
        project_id=project["id"],
        name="Alpha",
        due_date=(datetime.date.today() + datetime.timedelta(days=7)).isoformat(),
        percent=25,
    )

    with app.test_client() as client_http:
        resp = client_http.post(
            "/drp/",
            data={
                "task_name": "",
                "estimated_hours": "12",
                "deadline": "",
                "past_speed": "75",
                "daily_workload": "",
                "client_id": str(client["id"]),
                "project_id": str(project["id"]),
                "milestone_id": str(milestone["id"]),
                "use_calendar_blocks": "on",
            },
        )
        assert resp.status_code == 200

        entries = drp_hist.get_history()
        assert entries, "Prediction should be saved"
        latest = entries[0]
        assert latest["linked_context"]["client_name"] == "Acme"
        assert latest["linked_context"]["project_name"] == "Portal"
        assert latest["linked_context"]["milestone_name"] == "Alpha"

        report_resp = client_http.get("/drp/report")
        assert report_resp.status_code == 200


def test_accuracy_report_metrics(temp_data_dirs):
    future_deadline = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
    result = predict("Accuracy", 10, future_deadline, 80, 1)
    drp_hist.save_prediction(result)

    entry_id = drp_hist.get_history()[0]["id"]
    drp_hist.mark_prediction_completed(
        entry_id=entry_id,
        actual_hours=14.5,
        completed_on=(datetime.date.today() + datetime.timedelta(days=6)).isoformat(),
    )

    report = drp_hist.get_accuracy_report()
    assert report["count"] == 1
    assert report["mean_abs_error_pct"] > 0
    assert report["brier_score"] >= 0
