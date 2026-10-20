import sqlite3
import logging
import time
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

DB_FILE = "bot_database.db"
MAX_USERS = 200  # Максимум пользователей в базе

def init_db():
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

def get_unique_slugs(limit: int = 60) -> List[str]:
    """Возвращает список уникальных slug'ов (не более limit)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Берем последние limit записей по updated_at, чтобы проверять самых активных
    cursor.execute("""
        SELECT DISTINCT kick_slug FROM users
        ORDER BY updated_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def delete_user(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
