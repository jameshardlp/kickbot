import logging
from deepseek_api import generate_post
from telegram_sender import send_post_to_telegram
from state import get_current_slug

logger = logging.getLogger(__name__)

async def process_new_stream(stream_id: str, title: str, thumbnail_url: str = None, viewer_count: int = 0):
    slug = get_current_slug()
    logger.info(f"🎬 Обработка нового стрима: {title} (канал: {slug})")
    
    caption = await generate_post(stream_title=title, viewer_count=viewer_count, slug=slug)
    
    if not caption:
        logger.error("❌ Не удалось сгенерировать пост. Отправка отменена.")
        return

    await send_post_to_telegram(caption=caption, photo_url=thumbnail_url)
