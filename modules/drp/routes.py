from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash, session
from modules.drp import drp_bp
from modules.drp.predictor import predict
import modules.drp.history as hist
from modules.wft import helpers as wft_helpers


def _collect_milestones() -> list:
    milestones: list[dict] = []
    for project in wft_helpers.get_scoped_projects():
        project_id = project.get("id")
        if project_id is None:
            continue
        for milestone in wft_helpers.get_milestones(project_id):
            milestones.append({
                **milestone,
                "project_id": project_id,
                "project_name": project.get("project_name", "Project"),
                "client_name": project.get("client_name", "Unknown"),
            })
    return sorted(milestones, key=lambda m: (m.get("due_date", ""), m.get("name", "")))


def _blocked_dates_until(deadline_str: str) -> set[str]:
    blocked: set[str] = set()
    try:
        deadline = date.fromisoformat(deadline_str)
    except ValueError:
        return blocked

    today = date.today()
    if deadline < today:
        return blocked

    for block in wft_helpers.get_calendar_blocks():
        try:
            start = date.fromisoformat(block.get("date_from", ""))
            end = date.fromisoformat(block.get("date_to", ""))
        except ValueError:
            continue
        if end < start:
            start, end = end, start
        overlap_start = max(start, today + timedelta(days=1))
        overlap_end = min(end, deadline)
        if overlap_end < overlap_start:
            continue
        cursor = overlap_start
        while cursor <= overlap_end:
            blocked.add(cursor.isoformat())
            cursor += timedelta(days=1)

    return blocked


def _workload_hint(client_name: str = "") -> float:
    entries = wft_helpers.get_workhours()
    if not entries:
        return 0.0

    today = date.today()
    window_start = today - timedelta(days=21)
    total = 0.0
    days = 0
    for row in entries:
        if client_name and str(row.get("client", "")).strip() != client_name.strip():
            continue
        try:
            row_day = date.fromisoformat(str(row.get("date", "")))
        except ValueError:
            continue
        if row_day < window_start or row_day > today:
            continue
        try:
            total += float(row.get("hours", 0.0) or 0.0)
            days += 1
        except (TypeError, ValueError):
            continue
    if days == 0:
        return 0.0
    return round(total / max(days, 1), 1)


@drp_bp.route("/", methods=["GET", "POST"])
def index():
    result = None
    # Restore last inputs from session
    form_data = session.get("drp_last_form", {})
    clients = wft_helpers.get_clients()
    projects = wft_helpers.get_scoped_projects()
    milestones = _collect_milestones()

    if request.method == "POST":
        form_data = request.form.to_dict()
        selected_milestone_id = int(form_data.get("milestone_id") or 0)
        selected_milestone = next((m for m in milestones if m.get("id") == selected_milestone_id), None)

        if selected_milestone:
            if not (form_data.get("deadline") or "").strip():
                form_data["deadline"] = selected_milestone.get("due_date", "")
            if not (form_data.get("task_name") or "").strip():
                form_data["task_name"] = selected_milestone.get("name", "Unnamed Task")
            if not (form_data.get("project_id") or "").strip():
                form_data["project_id"] = str(selected_milestone.get("project_id") or "")

        if not str(form_data.get("daily_workload", "")).strip():
            selected_client_id = int(form_data.get("client_id") or 0)
            selected_client = next((c for c in clients if c.get("id") == selected_client_id), None)
            workload = _workload_hint(selected_client.get("name", "") if selected_client else "")
            form_data["daily_workload"] = str(workload)

        session["drp_last_form"] = form_data   # persist for next visit
        try:
            include_weekends = str(form_data.get("include_weekends", "")).lower() in {"1", "true", "on", "yes"}
            use_calendar = str(form_data.get("use_calendar_blocks", "")).lower() in {"1", "true", "on", "yes"}
            deadline = form_data.get("deadline", "")
            blocked_dates = _blocked_dates_until(deadline) if use_calendar else set()

            selected_client_id = int(form_data.get("client_id") or 0)
            selected_project_id = int(form_data.get("project_id") or 0)
            selected_client = next((c for c in clients if c.get("id") == selected_client_id), None)
            selected_project = next((p for p in projects if p.get("id") == selected_project_id), None)

            result = predict(
                task_name=form_data.get("task_name", "Unnamed Task"),
                estimated_hours=float(form_data.get("estimated_hours", 0)),
                deadline_str=deadline,
                past_speed=float(form_data.get("past_speed", 70)),
                daily_workload=float(form_data.get("daily_workload", 0)),
                working_hours_per_day=float(wft_helpers.get_settings().get("working_hours_per_day", 8.0) or 8.0),
                include_weekends=include_weekends,
                unavailable_dates=blocked_dates,
                linked_context={
                    "client_id": selected_client_id or None,
                    "client_name": selected_client.get("name") if selected_client else "",
                    "project_id": selected_project_id or None,
                    "project_name": selected_project.get("project_name") if selected_project else "",
                    "milestone_id": selected_milestone_id or None,
                    "milestone_name": selected_milestone.get("name") if selected_milestone else "",
                    "calendar_mode": "wft-blocks" if use_calendar else "manual",
                },
            )
            if "error" not in result:
                hist.save_prediction(result)
        except (ValueError, TypeError) as e:
            result = {"error": str(e)}
    return render_template(
        "drp/index.html",
        result=result,
        form_data=form_data,
        clients=clients,
        projects=projects,
        milestones=milestones,
    )


@drp_bp.route("/history")
def history():
    entries = hist.get_history()
    return render_template("drp/history.html", entries=entries)


@drp_bp.route("/history/complete/<int:entry_id>", methods=["POST"])
def complete_history(entry_id):
    actual_hours = request.form.get("actual_hours", "")
    completed_on = request.form.get("completed_on", "")
    try:
        if float(actual_hours) <= 0:
            raise ValueError("Actual hours must be greater than zero.")
        date.fromisoformat(completed_on)
    except ValueError:
        flash("Enter valid completion data (hours and date).", "warning")
        return redirect(url_for("drp.history"))

    updated = hist.mark_prediction_completed(entry_id, float(actual_hours), completed_on)
    if updated:
        flash("Prediction marked as completed. Accuracy report updated.", "success")
    else:
        flash("History entry not found.", "warning")
    return redirect(url_for("drp.history"))


@drp_bp.route("/history/delete/<int:entry_id>", methods=["POST"])
def delete_history(entry_id):
    hist.delete_history_entry(entry_id)
    flash("Prediction removed from history.", "info")
    return redirect(url_for("drp.history"))


@drp_bp.route("/history/clear", methods=["POST"])
def clear_history():
    hist.clear_history()
    flash("History cleared.", "info")
    return redirect(url_for("drp.history"))


@drp_bp.route("/report")
def report():
    return render_template("drp/report.html", report=hist.get_accuracy_report())
