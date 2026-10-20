import sqlite3
import logging
import time
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

DB_FILE = "bot_database.db"
MAX_USERS = 200

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Таблица пользователей (ЛС)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            kick_slug TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    # Таблица каналов (куда бот добавлен админом)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            chat_id INTEGER PRIMARY KEY,
            kick_slug TEXT NOT NULL,
            title TEXT,
            updated_at INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована (users + channels).")

# --- Пользователи (ЛС) ---

def set_user_slug(user_id: int, slug: str):
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
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    if count > MAX_USERS:
        cursor.execute("""
            DELETE FROM users
            WHERE user_id IN (
                SELECT user_id FROM users ORDER BY updated_at ASC LIMIT ?
            )
        """, (count - MAX_USERS,))
    conn.commit()
    conn.close()

def get_user_slug(user_id: int) -> Optional[str]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT kick_slug FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_users() -> List[Tuple[int, str]]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, kick_slug FROM users")
    rows = cursor.fetchall()
    conn.close()
    return rows

# --- Каналы (бот-админ) ---

def set_channel_slug(chat_id: int, slug: str, title: str = ""):
    """Привязывает канал к стримеру."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    now = int(time.time())
    cursor.execute("""
        INSERT INTO channels (chat_id, kick_slug, title, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            kick_slug = excluded.kick_slug,
            title = excluded.title,
            updated_at = excluded.updated_at
    """, (chat_id, slug, title, now))
    conn.commit()
    conn.close()

def get_channel_slug(chat_id: int) -> Optional[str]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT kick_slug FROM channels WHERE chat_id = ?", (chat_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_channels() -> List[Tuple[int, str, str]]:
    """Возвращает (chat_id, kick_slug, title)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, kick_slug, title FROM channels")
    rows = cursor.fetchall()
    conn.close()
    return rows

def remove_channel(chat_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
