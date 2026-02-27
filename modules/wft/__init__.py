from flask import Blueprint

wft_bp = Blueprint("wft", __name__, url_prefix="/wft")

from modules.wft import routes  # noqa: E402, F401
