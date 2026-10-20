import logging
import httpx
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def send_post_to_telegram(chat_id: int, caption: str, photo_url: str = None):
    """
    Отправляет пост. Если есть photo_url — сначала скачивает картинку, 
    затем отправляет её как файл (multipart), чтобы обойти ошибки Telegram с URL.
    """
    if not caption:
        logger.warning("⚠️ Пустой текст поста, отправка отменена.")
        return False

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if photo_url:
                # 1. Скачиваем картинку
                logger.info(f"📥 Скачиваю превью: {photo_url}")
                img_resp = await client.get(photo_url)
                if img_resp.status_code != 200:
                    logger.error(f"❌ Не удалось скачать превью: {img_resp.status_code}")
                    # Пробуем отправить хотя бы текст
                    return await _send_text_only(client, chat_id, caption)
                
                image_bytes = img_resp.content
                logger.info(f"✅ Превью скачано ({len(image_bytes)} байт)")

                # 2. Отправляем как файл (multipart)
                resp = await client.post(
                    f"{TELEGRAM_API_URL}/sendPhoto",
                    data={
                        "chat_id": chat_id,
                        "caption": caption,
                        "parse_mode": "HTML"
                    },
                    files={"photo": ("preview.jpg", image_bytes, "image/jpeg")}
                )
            else:
                return await _send_text_only(client, chat_id, caption)

            if resp.status_code == 200:
                logger.info(f"✅ Пост отправлен в {chat_id}")
                return True
            else:
                logger.error(f"❌ Ошибка Telegram API ({resp.status_code}): {resp.text}")
                return False

    except Exception as e:
        logger.error(f"❌ Исключение при отправке в Telegram: {e}")
        return False

async def _send_text_only(client: httpx.AsyncClient, chat_id: int, caption: str):
    """Запасной вариант: отправка только текста."""
    resp = await client.post(
        f"{TELEGRAM_API_URL}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": caption,
            "parse_mode": "HTML"
        }
    )
    if resp.status_code == 200:
        logger.info(f"✅ Текстовый пост отправлен в {chat_id}")
        return True
    else:
        logger.error(f"❌ Ошибка Telegram API (текст) ({resp.status_code}): {resp.text}")
        return False
