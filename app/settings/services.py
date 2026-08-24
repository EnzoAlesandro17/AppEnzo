import re
import unicodedata

from app.common.ids import generate_id
from app.settings import models

DEFAULT_CONTEXTS = [
    ("home", "Casa"),
    ("work", "Trabajo"),
    ("shopping", "Compras"),
    ("projects", "Proyectos"),
]


class ContextInUse(Exception):
    pass


class DuplicateContext(Exception):
    pass


def _slugify(label: str) -> str:
    normalized = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")
    return slug or generate_id().lower()


def seed_default_contexts(user_id: str) -> None:
    for position, (key, label) in enumerate(DEFAULT_CONTEXTS):
        if models.get_any_context_by_key(user_id, key) is None:
            models.insert_context(generate_id(), user_id, key, label, position)


def list_contexts(user_id: str) -> list[dict]:
    return models.list_contexts(user_id)


def get_label_map(user_id: str) -> dict[str, str]:
    return models.get_label_map(user_id)


def get_context(user_id: str, key: str) -> dict | None:
    return models.get_context_by_key(user_id, key)


def add_context(user_id: str, label: str) -> str:
    label = label.strip()
    key = _slugify(label)
    if models.get_context_by_key(user_id, key) is not None:
        raise DuplicateContext(key)
    context_id = generate_id()
    models.insert_context(context_id, user_id, key, label, models.next_position(user_id))
    return context_id


def rename_context(user_id: str, context_id: str, label: str) -> None:
    models.update_label(user_id, context_id, label.strip())


def delete_context(user_id: str, context_id: str, key: str) -> None:
    if models.count_tasks_using(user_id, key) > 0:
        raise ContextInUse(key)
    models.soft_delete(user_id, context_id)
