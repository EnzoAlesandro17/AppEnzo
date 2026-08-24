from datetime import date, timedelta

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.agenda import services
from app.auth.routes import login_required
from app.common.dates import DATE_FORMAT, parse_date

bp = Blueprint("agenda", __name__, url_prefix="/agenda", template_folder="templates")


def _parse_start(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return parse_date(value)
    except ValueError:
        return date.today()


@bp.route("/")
@login_required
def list_entries():
    start_date = _parse_start(request.args.get("from"))
    grouped = services.list_week(session["user_id"], start_date)
    days = sorted(grouped.keys())
    prev_week = (start_date - timedelta(days=7)).strftime(DATE_FORMAT)
    next_week = (start_date + timedelta(days=7)).strftime(DATE_FORMAT)
    return render_template(
        "agenda/list.html",
        grouped=grouped,
        days=days,
        kinds=services.KINDS,
        work_modes=services.WORK_MODES,
        kind_label=services.kind_label,
        start_date_str=start_date.strftime(DATE_FORMAT),
        prev_week=prev_week,
        next_week=next_week,
    )


@bp.route("/", methods=["POST"])
@login_required
def create_entry():
    kind = request.form["kind"]
    title = request.form.get("title", "")
    notes = request.form.get("notes") or None
    entry_date = parse_date(request.form["entry_date"])
    entry_time = request.form.get("entry_time") or None
    end_time = request.form.get("end_time") or None
    work_mode = request.form.get("work_mode") or None
    services.create_entry(
        session["user_id"], kind, title, notes, entry_date, entry_time, end_time, work_mode
    )
    return redirect(url_for("agenda.list_entries", **_redirect_from()))


@bp.route("/<entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(entry_id):
    services.delete_entry(session["user_id"], entry_id)
    return redirect(url_for("agenda.list_entries", **_redirect_from()))


def _redirect_from() -> dict:
    from_value = request.form.get("from")
    return {"from": from_value} if from_value else {}
