import os
from flask import Flask, render_template
from modules.drp import drp_bp
from modules.wft import wft_bp

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fltk-dev-secret-key")

app.register_blueprint(drp_bp)
app.register_blueprint(wft_bp)


@app.route("/")
def home():
    from modules.wft.helpers import get_earnings_summary, get_settings
    summary = get_earnings_summary()
    cfg = get_settings()
    summary["currency_symbol"] = cfg.get("currency_symbol", "$")
    return render_template("home.html", earnings_summary=summary)


if __name__ == "__main__":
    app.run(debug=True)
