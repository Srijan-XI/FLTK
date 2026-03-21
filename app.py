import logging
import os
import secrets

from flask import Flask, render_template, request, session, jsonify

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)

_secret = os.environ.get("SECRET_KEY", "")
_debug = os.environ.get("FLASK_DEBUG", "1") == "1"

if not _secret and not _debug:
    raise RuntimeError(
        "SECRET_KEY environment variable must be set in production. "
        "Set FLASK_DEBUG=1 to suppress this check during local development."
    )

app.secret_key = _secret or "fltk-dev-secret-do-not-use-in-prod"
app.config["CSRF_ENABLED"] = True

from modules.drp import drp_bp   # noqa: E402
from modules.wft import wft_bp   # noqa: E402
from modules.wft import helpers as wft_helpers  # noqa: E402

app.register_blueprint(drp_bp)
app.register_blueprint(wft_bp)


def _csrf_token() -> str:
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": _csrf_token}


@app.before_request
def csrf_protect():
    if not app.config.get("CSRF_ENABLED", True):
        return None
    if app.config.get("TESTING"):
        return None
    if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return None
    if request.endpoint == "static":
        return None

    expected = session.get("_csrf_token")
    submitted = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")

    if not expected or not submitted or not secrets.compare_digest(expected, submitted):
        log.warning("CSRF validation failed for endpoint=%s", request.endpoint)
        if request.is_json:
            return jsonify({"error": "Invalid CSRF token"}), 400
        return "Invalid CSRF token", 400
    return None


_integrity_report = wft_helpers.scan_data_integrity(auto_repair=False)
app.config["INTEGRITY_REPORT"] = _integrity_report
if _integrity_report.get("issues"):
    critical = sum(1 for issue in _integrity_report["issues"] if issue.get("severity") == "critical")
    log.warning(
        "Data integrity scanner found %s issue(s), %s critical.",
        len(_integrity_report["issues"]),
        critical,
    )

if os.environ.get("INTEGRITY_BLOCK_STARTUP", "0") == "1" and any(
    issue.get("severity") == "critical" for issue in _integrity_report.get("issues", [])
):
    raise RuntimeError(
        "Critical data integrity issues detected. "
        "Set INTEGRITY_BLOCK_STARTUP=0 to start anyway and repair via /wft/integrity."
    )


@app.route("/")
def home():
    from modules.wft.helpers import (
        get_earnings_summary,
        get_settings,
        get_due_recurring_invoices,
        get_upcoming_milestones,
        get_audit_trail,
        list_restore_points,
    )
    summary = get_earnings_summary()
    cfg = get_settings()
    summary["currency_symbol"] = cfg.get("currency_symbol", "$")
    integrity_report = app.config.get("INTEGRITY_REPORT") or {"counts": {"critical": 0, "major": 0, "minor": 0}}
    return render_template(
        "home.html",
        earnings_summary=summary,
        recurring_due_count=len(get_due_recurring_invoices()),
        upcoming_milestones_count=len(get_upcoming_milestones(14)),
        integrity_counts=integrity_report.get("counts", {}),
        restore_points_count=len(list_restore_points()),
        recent_audit_events=get_audit_trail(limit=5),
    )


if __name__ == "__main__":
    app.run(debug=_debug)
