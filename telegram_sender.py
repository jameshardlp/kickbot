import logging
import httpx
from config import TELEGRAM_BOT_TOKEN

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def send_post_to_telegram(chat_id: int, caption: str, photo_url: str = None):
    if not caption:
        logger.warning("⚠️ Пустой текст поста, отправка отменена.")
        return False

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if photo_url:
                # 1. Скачиваем картинку сами
                logger.info(f"📥 Скачиваю превью: {photo_url}")
                img_resp = await client.get(photo_url)
                
                if img_resp.status_code == 200:
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
                    logger.error(f"❌ Не удалось скачать превью: {img_resp.status_code}")
                    # Запасной вариант: шлём только текст
                    resp = await client.post(
                        f"{TELEGRAM_API_URL}/sendMessage",
                        json={"chat_id": chat_id, "text": caption, "parse_mode": "HTML"}
                    )
            else:
                resp = await client.post(
                    f"{TELEGRAM_API_URL}/sendMessage",
                    json={"chat_id": chat_id, "text": caption, "parse_mode": "HTML"}
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
