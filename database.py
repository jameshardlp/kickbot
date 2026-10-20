import sqlite3
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

DB_FILE = "bot_database.db"
MAX_USERS = 200  # Максимальное количество пользователей в базе

def init_db():
    """Создаёт таблицу users, если её нет."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            kick_slug TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована.")

def set_user_slug(user_id: int, slug: str):
    """Сохраняет или обновляет slug для пользователя."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = int(time.time())
    
    cursor.execute("""
        INSERT INTO users (user_id, kick_slug, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            kick_slug = excluded.kick_slug,
            updated_at = excluded.updated_at
    """, (user_id, slug, now))
    
    # Проверяем лимит
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    
    if count > MAX_USERS:
        # Удаляем самого старого пользователя (по updated_at)
        cursor.execute("""
            DELETE FROM users
            WHERE user_id IN (
                SELECT user_id FROM users ORDER BY updated_at ASC LIMIT ?
            )
        """, (count - MAX_USERS,))
        logger.info(f"🗑 Удалено {count - MAX_USERS} старых пользователей (лимит {MAX_USERS}).")
    
    conn.commit()
    conn.close()

def get_user_slug(user_id: int) -> Optional[str]:
    """Возвращает slug пользователя или None, если его нет в базе."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT kick_slug FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_users() -> list[tuple[int, str]]:
    """Возвращает список всех пользователей (user_id, kick_slug)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, kick_slug FROM users")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_user(user_id: int):
    """Удаляет пользователя из базы (например, по команде /стоп)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()