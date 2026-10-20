import logging
from deepseek_api import generate_post
from telegram_sender import send_post_to_telegram

logger = logging.getLogger(__name__)

async def process_new_stream(chat_id: int, stream_id: str, title: str, thumbnail_url: str = None, viewer_count: int = 0, slug: str = None):
    """
    Генерирует пост и отправляет его в указанный chat_id.
    """
    if not slug:
        logger.error("❌ Не указан slug для генерации поста.")
        return

    logger.info(f"🎬 Обработка стрима {slug} для чата {chat_id}")
    
    caption = await generate_post(stream_title=title, viewer_count=viewer_count, slug=slug)
    
    if not caption:
        logger.error("❌ Не удалось сгенерировать пост. Отправка отменена.")
        return

    await send_post_to_telegram(chat_id, caption, photo_url=thumbnail_url)
