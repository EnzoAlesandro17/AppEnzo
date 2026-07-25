from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.auth import services

bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="templates")


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = services.authenticate(email, password)
        if user is None:
            error = "Email o contraseña incorrectos"
        else:
            session.clear()
            session["user_id"] = user["id"]
            return redirect(request.args.get("next") or url_for("main.index"))
    return render_template("auth/login.html", error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
