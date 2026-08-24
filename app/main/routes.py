from datetime import date

from flask import Blueprint, render_template, session

from app.auth.routes import login_required
from app.main import services

bp = Blueprint("main", __name__, template_folder="templates")


@bp.route("/")
@login_required
def index():
    dashboard = services.get_dashboard(session["user_id"], date.today())
    return render_template("main/index.html", dashboard=dashboard)
