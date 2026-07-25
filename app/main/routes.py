from flask import Blueprint, render_template

from app.auth.routes import login_required

bp = Blueprint("main", __name__, template_folder="templates")


@bp.route("/")
@login_required
def index():
    return render_template("main/index.html")
