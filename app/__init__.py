from dotenv import load_dotenv
from flask import Flask

from app.config import Config


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object(Config)

    from app.auth.cli import create_user_command
    from app.auth.routes import bp as auth_bp
    from app.cards.routes import bp as cards_bp
    from app.main.routes import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(cards_bp)
    app.cli.add_command(create_user_command)

    return app
