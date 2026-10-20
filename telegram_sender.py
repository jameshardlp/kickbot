import logging
import httpx
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def send_post_to_telegram(caption: str, photo_url: str = None):
    """
    Отправляет пост в Telegram. Если есть photo_url — отправляет фото с подписью,
    иначе — просто текстовое сообщение.
    """
    if not caption:
        logger.warning("⚠️ Пустой текст поста, отправка отменена.")
        return False

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if photo_url:
                # Отправляем фото с подписью
                logger.info(f"📤 Отправка фото с подписью в канал {TELEGRAM_CHANNEL_ID}...")
                resp = await client.post(
                    f"{TELEGRAM_API_URL}/sendPhoto",
                    json={
                        "chat_id": TELEGRAM_CHANNEL_ID,
                        "photo": photo_url,
                        "caption": caption,
                        "parse_mode": "HTML"
                    }
                )
            else:
                # Если фото нет — отправляем только текст
                logger.info(f"📤 Отправка текстового поста в канал {TELEGRAM_CHANNEL_ID}...")
                resp = await client.post(
                    f"{TELEGRAM_API_URL}/sendMessage",
                    json={
                        "chat_id": TELEGRAM_CHANNEL_ID,
                        "text": caption,
                        "parse_mode": "HTML"
                    }
                )

            if resp.status_code == 200:
                logger.info("✅ Пост успешно отправлен в Telegram!")
                return True
            else:
                logger.error(f"❌ Ошибка Telegram API ({resp.status_code}): {resp.text}")
                return False

    except Exception as e:
        logger.error(f"❌ Исключение при отправке в Telegram: {e}")
        return False