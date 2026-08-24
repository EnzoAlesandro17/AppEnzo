from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from app.common.dates import format_day_label, format_long_date_es, format_month_es
from app.common.money import format_amount
from app.common.today import badge_class, time_range_label
from app.config import Config


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(Config)
    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)

    app.jinja_env.filters["format_day_label"] = format_day_label
    app.jinja_env.filters["format_long_date_es"] = format_long_date_es
    app.jinja_env.filters["format_month_es"] = format_month_es
    app.jinja_env.filters["format_amount"] = format_amount
    app.jinja_env.filters["badge_class"] = badge_class
    app.jinja_env.filters["time_range_label"] = time_range_label

    from app.agenda.routes import bp as agenda_bp
    from app.auth.cli import create_user_command
    from app.auth.routes import bp as auth_bp
    from app.budget.routes import bp as budget_bp
    from app.db.cli import init_db_command
    from app.main.routes import bp as main_bp
    from app.settings.routes import bp as settings_bp
    from app.tasks.routes import bp as tasks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(agenda_bp)
    app.register_blueprint(budget_bp)
    app.register_blueprint(settings_bp)
    app.cli.add_command(create_user_command)
    app.cli.add_command(init_db_command)

    return app
