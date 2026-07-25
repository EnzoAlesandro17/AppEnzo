import secrets
import string

_ALPHABET = string.ascii_uppercase + string.digits
ID_LENGTH = 12


def generate_id() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(ID_LENGTH))
