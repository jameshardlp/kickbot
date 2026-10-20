import logging
from deepseek_api import generate_post
from telegram_sender import send_post_to_telegram

logger = logging.getLogger(__name__)

async def process_new_stream(stream_id: str, title: str, thumbnail_url: str = None, viewer_count: int = 0):
    """
    Общая логика: генерация поста через DeepSeek и отправка в Telegram.
    """
    logger.info(f"🎬 Обработка нового стрима: {title}")
    
    # 1. Генерируем текст
    caption = await generate_post(stream_title=title, viewer_count=viewer_count)
    
    if not caption:
        logger.error("❌ Не удалось сгенерировать пост. Отправка отменена.")
        return

    # 2. Отправляем в Telegram (с фото, если есть)
    await send_post_to_telegram(caption=caption, photo_url=thumbnail_url)