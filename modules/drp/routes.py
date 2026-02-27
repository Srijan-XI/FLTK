from flask import render_template, request, redirect, url_for, flash, session
from modules.drp import drp_bp
from modules.drp.predictor import predict
import modules.drp.history as hist


@drp_bp.route("/", methods=["GET", "POST"])
def index():
    result = None
    # Restore last inputs from session
    form_data = session.get("drp_last_form", {})

    if request.method == "POST":
        form_data = request.form.to_dict()
        session["drp_last_form"] = form_data   # persist for next visit
        try:
            result = predict(
                task_name=form_data.get("task_name", "Unnamed Task"),
                estimated_hours=float(form_data.get("estimated_hours", 0)),
                deadline_str=form_data.get("deadline", ""),
                past_speed=float(form_data.get("past_speed", 70)),
                daily_workload=float(form_data.get("daily_workload", 0)),
            )
            if "error" not in result:
                hist.save_prediction(result)
        except (ValueError, TypeError) as e:
            result = {"error": str(e)}
    return render_template("drp/index.html", result=result, form_data=form_data)


@drp_bp.route("/history")
def history():
    entries = hist.get_history()
    return render_template("drp/history.html", entries=entries)


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
