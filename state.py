import os
import logging

logger = logging.getLogger(__name__)

SLUG_FILE = "current_slug.txt"
STREAM_FILE = "last_stream_id.txt"

def get_current_slug() -> str:
    """Возвращает текущий отслеживаемый slug (по умолчанию maddyson)."""
    if os.path.exists(SLUG_FILE):
        try:
            with open(SLUG_FILE, "r") as f:
                slug = f.read().strip()
                if slug:
                    return slug
        except Exception as e:
            logger.error(f"Ошибка чтения {SLUG_FILE}: {e}")
    return "maddyson"

def set_current_slug(slug: str):
    """Устанавливает новый slug."""
    try:
        with open(SLUG_FILE, "w") as f:
            f.write(slug)
        logger.info(f"💾 Сохранён новый slug: {slug}")
    except Exception as e:
        logger.error(f"Ошибка записи {SLUG_FILE}: {e}")

def get_last_stream_id() -> str | None:
    """Возвращает ID последнего обработанного стрима."""
    if os.path.exists(STREAM_FILE):
        try:
            with open(STREAM_FILE, "r") as f:
                sid = f.read().strip()
                if sid:
                    return sid
        except Exception as e:
            logger.error(f"Ошибка чтения {STREAM_FILE}: {e}")
    return None

def set_last_stream_id(stream_id: str | None):
    """Сохраняет ID последнего обработанного стрима."""
    try:
        with open(STREAM_FILE, "w") as f:
            f.write(stream_id or "")
    except Exception as e:
        logger.error(f"Ошибка записи {STREAM_FILE}: {e}")
