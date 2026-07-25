from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from app.auth.routes import login_required
from app.cards import services
from app.common.dates import DATE_FORMAT, parse_date, parse_optional_date

bp = Blueprint("cards", __name__, url_prefix="/cards", template_folder="templates")

MONTHS = [
    (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
    (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
    (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
]


@bp.route("/")
@login_required
def list_cards():
    cards = services.list_cards(session["user_id"])
    return render_template("cards/list.html", cards=cards)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new_card():
    if request.method == "POST":
        services.create_card(
            user_id=session["user_id"],
            name=request.form["name"],
            bank=request.form.get("bank") or None,
            last_four_digits=request.form.get("last_four_digits") or None,
        )
        return redirect(url_for("cards.list_cards"))
    return render_template("cards/new.html")


def _get_owned_card(card_id: str) -> dict:
    card = services.get_card(card_id, session["user_id"])
    if card is None:
        abort(404)
    return card


@bp.route("/<card_id>")
@login_required
def card_detail(card_id):
    card = _get_owned_card(card_id)
    current_statement = services.get_current_statement(card_id)
    view = services.get_statement_view(card_id, current_statement["id"])
    return render_template("cards/home.html", card=card, view=view, today=date.today().strftime(DATE_FORMAT))


@bp.route("/<card_id>/entries")
@login_required
def entries_list(card_id):
    card = _get_owned_card(card_id)
    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    entries_page = services.list_entries_page(card_id, page)
    return render_template("cards/entries.html", card=card, page_data=entries_page)


@bp.route("/<card_id>/statements")
@login_required
def statement_list(card_id):
    card = _get_owned_card(card_id)
    statements = services.list_statements(card_id)
    current_year = date.today().year
    year_options = list(range(current_year - 10, current_year + 2))
    return render_template(
        "cards/statements.html",
        card=card,
        statements=statements,
        year_options=year_options,
        current_year=current_year,
        months=MONTHS,
    )


@bp.route("/<card_id>/statements/new", methods=["POST"])
@login_required
def new_statement(card_id):
    _get_owned_card(card_id)
    year = int(request.form["year"])
    month = int(request.form["month"])
    statement = services.create_statement_for_period(card_id, year, month)
    return redirect(url_for("cards.statement_detail", card_id=card_id, statement_id=statement["id"]))


@bp.route("/<card_id>/statements/<statement_id>/delete", methods=["POST"])
@login_required
def delete_statement(card_id, statement_id):
    _get_owned_card(card_id)
    try:
        services.delete_statement(card_id, statement_id)
    except ValueError:
        flash("No se puede eliminar: el resumen tiene movimientos.")
        return redirect(url_for("cards.statement_detail", card_id=card_id, statement_id=statement_id))
    return redirect(url_for("cards.statement_list", card_id=card_id))


@bp.route("/<card_id>/statements/<statement_id>", methods=["GET", "POST"])
@login_required
def statement_detail(card_id, statement_id):
    card = _get_owned_card(card_id)
    if request.method == "POST":
        try:
            closing_date = parse_optional_date(request.form.get("closing_date"))
            due_date = parse_optional_date(request.form.get("due_date"))
        except ValueError:
            flash("Fecha inválida (formato dd-mm-aaaa)")
            return redirect(url_for("cards.statement_detail", card_id=card_id, statement_id=statement_id))

        services.update_statement(card_id, statement_id, closing_date=closing_date, due_date=due_date)
        return redirect(url_for("cards.statement_detail", card_id=card_id, statement_id=statement_id))

    view = services.get_statement_view(card_id, statement_id)
    if view["statement"] is None:
        abort(404)
    return render_template("cards/detail.html", card=card, view=view)


@bp.route("/<card_id>/entries/new", methods=["POST"])
@login_required
def new_entry(card_id):
    _get_owned_card(card_id)

    entry_type = request.form["entry_type"]
    currency = request.form["currency"]
    description = request.form.get("description") or None
    installment_count = int(request.form.get("installment_count") or 1)

    try:
        amount = Decimal(request.form["amount"])
    except InvalidOperation:
        flash("Monto inválido")
        return redirect(url_for("cards.card_detail", card_id=card_id))

    try:
        entry_date = parse_date(request.form["date"])
    except ValueError:
        flash("Fecha inválida (formato dd-mm-aaaa)")
        return redirect(url_for("cards.card_detail", card_id=card_id))

    if entry_type == "expense" and installment_count > 1:
        statement = services.add_installment_purchase(
            card_id, currency, amount, installment_count, description, entry_date
        )
    elif entry_type == "expense":
        statement = services.add_expense(card_id, currency, amount, description, entry_date)
    else:
        statement = services.add_payment(card_id, currency, amount, description, entry_date)

    return redirect(url_for("cards.statement_detail", card_id=card_id, statement_id=statement["id"]))


@bp.route("/<card_id>/statements/<statement_id>/entries/<entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(card_id, statement_id, entry_id):
    _get_owned_card(card_id)
    try:
        services.delete_entry(card_id, entry_id)
    except ValueError:
        abort(404)
    next_url = request.form.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("cards.statement_detail", card_id=card_id, statement_id=statement_id))
