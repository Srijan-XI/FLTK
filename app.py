import logging
import os

from flask import Flask, render_template

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

from modules.drp import drp_bp   # noqa: E402
from modules.wft import wft_bp   # noqa: E402

app.register_blueprint(drp_bp)
app.register_blueprint(wft_bp)


@app.route("/")
def home():
    from modules.wft.helpers import (
        get_earnings_summary,
        get_settings,
        get_due_recurring_invoices,
        get_upcoming_milestones,
    )
    summary = get_earnings_summary()
    cfg = get_settings()
    summary["currency_symbol"] = cfg.get("currency_symbol", "$")
    return render_template(
        "home.html",
        earnings_summary=summary,
        recurring_due_count=len(get_due_recurring_invoices()),
        upcoming_milestones_count=len(get_upcoming_milestones(14)),
    )


if __name__ == "__main__":
    app.run(debug=_debug)
