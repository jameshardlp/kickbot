import logging
import httpx
from config import DEEPSEEK_API_KEY, KICK_CHANNEL_SLUG

logger = logging.getLogger(__name__)

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

async def generate_post(stream_title: str, viewer_count: int = 0) -> str:
    """
    Генерирует пост про начало стрима в стиле автора канала maddysontg.
    Возвращает текст поста или пустую строку при ошибке.
    """
    if not DEEPSEEK_API_KEY:
        logger.error("❌ Нет DEEPSEEK_API_KEY")
        return ""

    # Формируем системный промпт с характером автора
    system_prompt = """Ты — автор телеграм-канала. Ты циничный, агрессивный и очень самоироничный человек.
Ты презираешь фальшь, накрутки и «полезность». Ты открыто признаёшь свои слабости (лень, нежелание быть «мужиком»), и это делает твои тексты сильнее.
Ты используешь мат как естественную часть речи (но не ради мата, а для усиления мысли).
Ты не строишь из себя «крутого» — ты можешь написать, что тебе насрать на всех, но при этом сам сидишь и смотришь стримы.

В твоём окружении есть Дианочка — рекламный агент, которая забирает 80% денег у стримеров, оставляя им 20%. Ты её ненавидишь и можешь вскользь упомянуть, но не зацикливайся на ней.

Твоя задача — написать короткий пост (максимум 300 символов, 2 абзаца) о том, что стример по имени {slug} только что запустил стрим на Kick.
Название стрима: "{title}".
Ты должен прокомментировать это в своём стиле: с матом, шутками, цинизмом и самоиронией. Не пиши «сижу вот» или «вчера сидел». Не упоминай, что ты сам стример. Просто выскажи своё мнение о том, что этот человек снова в эфире.

Только текст поста, без пояснений и кавычек."""

    user_prompt = f"Стример {KICK_CHANNEL_SLUG} запустил стрим. Название: «{stream_title}». Зрителей на старте: {viewer_count}. Напиши пост."

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt.format(slug=KICK_CHANNEL_SLUG, title=stream_title)},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 1.0,
        "max_tokens": 300,
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(DEEPSEEK_URL, headers=headers, json=payload)
            
            if response.status_code != 200:
                logger.error(f"❌ DeepSeek вернул ошибку {response.status_code}: {response.text}")
                return ""
            
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            # Простая очистка от возможных кавычек и лишних пробелов
            content = content.strip('"').strip("«").strip("»").strip()
            
            logger.info(f"✅ Пост сгенерирован ({len(content)} символов)")
            return content

    except Exception as e:
        logger.error(f"❌ Ошибка при генерации через DeepSeek: {e}")
        return ""