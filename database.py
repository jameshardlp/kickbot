import sqlite3
import logging
import time
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

DB_FILE = "bot_database.db"
MAX_USERS = 200
MAX_OWNERS = 3

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Пользователи (ЛС) — те, кто получает посты
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            kick_slug TEXT NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    # Каналы (куда бот добавлен админом)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            chat_id INTEGER PRIMARY KEY,
            kick_slug TEXT NOT NULL,
            title TEXT,
            updated_at INTEGER NOT NULL
        )
    """)
    # Состояние стримов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stream_state (
            slug TEXT PRIMARY KEY,
            stream_id TEXT
        )
    """)
    # Владельцы (до 3 человек, кто может настраивать бота)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS owners (
            user_id INTEGER PRIMARY KEY,
            added_at INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована (users + channels + stream_state + owners).")

# --- Пользователи ---
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

# --- Каналы ---
def set_channel_slug(chat_id: int, slug: str, title: str = ""):
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

def get_all_channels() -> List[Tuple[int, str, str]]:
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

# --- Состояние стримов ---
def get_stream_state(slug: str) -> Optional[str]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT stream_id FROM stream_state WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def set_stream_state(slug: str, stream_id: Optional[str]):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if stream_id:
        cursor.execute("""
            INSERT INTO stream_state (slug, stream_id)
            VALUES (?, ?)
            ON CONFLICT(slug) DO UPDATE SET stream_id = excluded.stream_id
        """, (slug, stream_id))
    else:
        cursor.execute("DELETE FROM stream_state WHERE slug = ?", (slug,))
    conn.commit()
    conn.close()

# --- Владельцы ---
def add_owner(user_id: int) -> bool:
    """Добавляет владельца. Возвращает False, если лимит (3) превышен."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Проверяем, не владелец ли уже
    cursor.execute("SELECT 1 FROM owners WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        conn.close()
        return True  # уже есть
    # Проверяем лимит
    cursor.execute("SELECT COUNT(*) FROM owners")
    count = cursor.fetchone()[0]
    if count >= MAX_OWNERS:
        conn.close()
        return False
    cursor.execute("INSERT INTO owners (user_id, added_at) VALUES (?, ?)", (user_id, int(time.time())))
    conn.commit()
    conn.close()
    return True

def remove_owner(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM owners WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_owner(user_id: int) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM owners WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def get_all_owners() -> List[int]:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM owners ORDER BY added_at")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]
