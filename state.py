import os

SLUG_FILE = "current_slug.txt"

def get_current_slug() -> str:
    """Возвращает текущий отслеживаемый slug (по умолчанию maddyson)."""
    if os.path.exists(SLUG_FILE):
        with open(SLUG_FILE, "r") as f:
            return f.read().strip()
    return "maddyson"  # значение по умолчанию

def set_current_slug(slug: str):
    """Устанавливает новый slug."""
    with open(SLUG_FILE, "w") as f:
        f.write(slug)