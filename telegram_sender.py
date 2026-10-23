import logging
import httpx
import asyncio
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Простая защита от спама в один чат: не чаще 1 сообщения в 3 секунды
_last_send_time = {}

async def send_post_to_telegram(chat_id: int, caption: str, photo_url: str = None):
    if not caption:
        logger.warning("⚠️ Пустой текст поста, отправка отменена.")
        return False

    # Защита от слишком частой отправки в один и тот же чат
    now = asyncio.get_event_loop().time()
    last = _last_send_time.get(chat_id, 0)
    if now - last < 3:  # 3 секунды между сообщениями в один чат
        await asyncio.sleep(3 - (now - last))
    _last_send_time[chat_id] = asyncio.get_event_loop().time()

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if photo_url:
                # 1. Скачиваем картинку
                logger.info(f"📥 Скачиваю превью: {photo_url}")
                img_resp = await client.get(photo_url)
                
                if img_resp.status_code == 200:
                    image_bytes = img_resp.content
                    size_mb = len(image_bytes) / (1024 * 1024)
                    
                    # Проверка лимита Telegram (10 МБ для multipart)
                    if size_mb > 10:
                        logger.warning(f"⚠️ Превью слишком большое ({size_mb:.2f} МБ), отправляю только текст.")
                        return await _send_text_only(client, chat_id, caption)
                    
                    logger.info(f"✅ Превью скачано ({size_mb:.2f} МБ)")

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
                    logger.error(f"❌ Не удалось скачать превью: {img_resp.status_code}")
                    return await _send_text_only(client, chat_id, caption)
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
    resp = await client.post(
        f"{TELEGRAM_API_URL}/sendMessage",
        json={"chat_id": chat_id, "text": caption, "parse_mode": "HTML"}
    )
    if resp.status_code == 200:
        logger.info(f"✅ Текстовый пост отправлен в {chat_id}")
        return True
    else:
        logger.error(f"❌ Ошибка Telegram API (текст) ({resp.status_code}): {resp.text}")
        return False
