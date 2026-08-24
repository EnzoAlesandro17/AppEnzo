from datetime import date

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from app.auth.routes import login_required
from app.common.dates import parse_optional_date
from app.settings import services as settings_services
from app.tasks import services

bp = Blueprint("tasks", __name__, url_prefix="/tasks", template_folder="templates")


@bp.route("/")
@login_required
def list_tasks():
    grouped = services.list_grouped(session["user_id"])
    contexts = settings_services.list_contexts(session["user_id"])
    return render_template(
        "tasks/list.html",
        grouped=grouped,
        contexts=contexts,
        statuses=services.STATUSES,
        today=date.today(),
    )


@bp.route("/", methods=["POST"])
@login_required
def create_task():
    title = request.form["title"]
    context = request.form["context"]
    notes = request.form.get("notes") or None
    due_date = parse_optional_date(request.form.get("due_date"))
    due_time = request.form.get("due_time") or None
    end_time = request.form.get("end_time") or None
    services.create_task(session["user_id"], context, title, notes, due_date, due_time, end_time)
    return redirect(url_for("tasks.list_tasks"))


@bp.route("/<task_id>")
@login_required
def task_detail(task_id):
    task = services.get_task_detail(session["user_id"], task_id)
    if task is None:
        abort(404)
    label_map = settings_services.get_label_map(session["user_id"])
    return render_template(
        "tasks/detail.html",
        task=task,
        context_label=label_map.get(task["context"], task["context"]),
        statuses=services.STATUSES,
        today=date.today(),
    )


@bp.route("/<task_id>/status", methods=["POST"])
@login_required
def update_status(task_id):
    status = request.form["status"]
    services.set_status(session["user_id"], task_id, status)
    next_url = request.form.get("next")
    if next_url:
        return redirect(next_url)
    return redirect(url_for("tasks.list_tasks", _anchor=f"task-{task_id}"))


@bp.route("/<task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    services.delete_task(session["user_id"], task_id)
    return redirect(url_for("tasks.list_tasks"))


@bp.route("/<task_id>/steps", methods=["POST"])
@login_required
def add_step(task_id):
    title = request.form["title"]
    services.add_step(session["user_id"], task_id, title)
    return redirect(url_for("tasks.task_detail", task_id=task_id))


@bp.route("/<task_id>/steps/<step_id>/toggle", methods=["POST"])
@login_required
def toggle_step(task_id, step_id):
    done = request.form.get("done") == "1"
    services.toggle_step(session["user_id"], step_id, done)
    return redirect(url_for("tasks.task_detail", task_id=task_id, _anchor=f"step-{step_id}"))


@bp.route("/<task_id>/steps/<step_id>/delete", methods=["POST"])
@login_required
def delete_step(task_id, step_id):
    services.delete_step(session["user_id"], step_id)
    return redirect(url_for("tasks.task_detail", task_id=task_id))
