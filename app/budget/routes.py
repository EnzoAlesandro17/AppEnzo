from datetime import date

from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from app.auth.routes import login_required
from app.budget import services
from app.common.dates import parse_optional_date
from app.common.money import parse_amount

bp = Blueprint("budget", __name__, url_prefix="/budget", template_folder="templates")


def _parse_period(value: str | None) -> date:
    if value:
        try:
            year, month = value.split("-")
            return date(int(year), int(month), 1)
        except (ValueError, TypeError):
            pass
    today = date.today()
    return date(today.year, today.month, 1)


def _shift_period(period: date, months: int) -> date:
    month_index = period.month - 1 + months
    year = period.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


@bp.route("/")
@login_required
def list_items():
    period = _parse_period(request.args.get("period"))
    view = services.get_period_view(session["user_id"], period)
    return render_template(
        "budget/list.html",
        view=view,
        statuses=services.STATUSES,
        period_str=period.strftime("%Y-%m"),
        prev_period=_shift_period(period, -1).strftime("%Y-%m"),
        next_period=_shift_period(period, 1).strftime("%Y-%m"),
    )


@bp.route("/", methods=["POST"])
@login_required
def create_item():
    period = _parse_period(request.form.get("period"))
    title = request.form["title"]
    amount = parse_amount(request.form["amount"])
    due_date = parse_optional_date(request.form.get("due_date"))
    notes = request.form.get("notes") or None
    is_recurring = request.form.get("is_recurring") == "on"
    services.create_item(session["user_id"], period, title, amount, due_date, notes, is_recurring)
    return redirect(url_for("budget.list_items", period=period.strftime("%Y-%m")))


@bp.route("/<item_id>/edit")
@login_required
def edit_item(item_id):
    item = services.get_item(session["user_id"], item_id)
    if item is None:
        abort(404)
    return render_template("budget/edit.html", item=item)


@bp.route("/<item_id>/edit", methods=["POST"])
@login_required
def update_item(item_id):
    title = request.form["title"]
    amount = parse_amount(request.form["amount"])
    due_date = parse_optional_date(request.form.get("due_date"))
    notes = request.form.get("notes") or None
    is_recurring = request.form.get("is_recurring") == "on"
    services.update_item(session["user_id"], item_id, title, amount, due_date, notes, is_recurring)
    return redirect(url_for("budget.list_items", period=request.form.get("period")))


@bp.route("/<item_id>/status", methods=["POST"])
@login_required
def update_status(item_id):
    status = request.form["status"]
    services.set_status(session["user_id"], item_id, status)
    return redirect(
        url_for("budget.list_items", period=request.form.get("period"), _anchor=f"item-{item_id}")
    )


@bp.route("/<item_id>/delete", methods=["POST"])
@login_required
def delete_item(item_id):
    services.delete_item(session["user_id"], item_id)
    return redirect(url_for("budget.list_items", period=request.form.get("period")))
