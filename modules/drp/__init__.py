from flask import Blueprint

drp_bp = Blueprint("drp", __name__, url_prefix="/drp")

from modules.drp import routes  # noqa: E402, F401
