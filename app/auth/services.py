import bcrypt

from app.auth import models
from app.common.ids import generate_id


class EmailAlreadyRegistered(Exception):
    pass


def create_user(email: str, password: str) -> str:
    if models.get_user_by_email(email) is not None:
        raise EmailAlreadyRegistered(email)
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = generate_id()
    models.insert_user(user_id, email, password_hash)
    return user_id


def authenticate(email: str, password: str) -> dict | None:
    user = models.get_user_by_email(email)
    if user is None:
        return None
    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return None
    return user
