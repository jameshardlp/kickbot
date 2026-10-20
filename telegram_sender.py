import logging
import httpx
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def send_post_to_telegram(chat_id: int, caption: str, photo_url: str = None):
    """
    Отправляет пост в указанный чат (канал или ЛС).
    """
    if not caption:
        logger.warning("⚠️ Пустой текст поста, отправка отменена.")
        return False

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if photo_url:
                resp = await client.post(
                    f"{TELEGRAM_API_URL}/sendPhoto",
                    json={
                        "chat_id": chat_id,
                        "photo": photo_url,
                        "caption": caption,
                        "parse_mode": "HTML"
                    }
                )
            else:
                resp = await client.post(
                    f"{TELEGRAM_API_URL}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": caption,
                        "parse_mode": "HTML"
                    }
                )

            if resp.status_code == 200:
                logger.info(f"✅ Пост отправлен в {chat_id}")
                return True
            else:
                logger.error(f"❌ Ошибка Telegram API ({resp.status_code}): {resp.text}")
                return False

    except Exception as e:
        logger.error(f"❌ Исключение при отправке в Telegram: {e}")
        return False
