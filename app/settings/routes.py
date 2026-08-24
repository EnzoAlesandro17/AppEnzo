from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.auth.routes import login_required
from app.settings import services

bp = Blueprint("settings", __name__, url_prefix="/settings", template_folder="templates")


@bp.route("/")
@login_required
def index():
    contexts = services.list_contexts(session["user_id"])
    return render_template("settings/index.html", contexts=contexts)


@bp.route("/contexts", methods=["POST"])
@login_required
def add_context():
    label = request.form["label"]
    try:
        services.add_context(session["user_id"], label)
    except services.DuplicateContext:
        flash("Ya existe un rubro con ese nombre.")
    return redirect(url_for("settings.index"))


@bp.route("/contexts/<context_id>/rename", methods=["POST"])
@login_required
def rename_context(context_id):
    label = request.form["label"]
    services.rename_context(session["user_id"], context_id, label)
    return redirect(url_for("settings.index"))


@bp.route("/contexts/<context_id>/delete", methods=["POST"])
@login_required
def delete_context(context_id):
    key = request.form["key"]
    try:
        services.delete_context(session["user_id"], context_id, key)
    except services.ContextInUse:
        flash("No se puede borrar: todavía hay tareas usando este rubro.")
    return redirect(url_for("settings.index"))
