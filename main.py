import os
import uvicorn
import logging
import httpx
import asyncio
from fastapi import FastAPI

from config import check_config, KICK_CLIENT_ID, KICK_CLIENT_SECRET, KICK_CHANNEL_SLUG
from kick_webhook import router as kick_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

check_config()

app = FastAPI(title="Kick Alert Bot")
app.include_router(kick_router)

# Глобальная переменная для отслеживания последнего обработанного стрима
last_stream_id = None

async def get_kick_token():
    """Получает app access token для Kick API."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://id.kick.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": KICK_CLIENT_ID,
                "client_secret": KICK_CLIENT_SECRET,
            }
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
        logger.error(f"❌ Ошибка получения токена: {resp.status_code}")
        return None

async def check_stream_status():
    """Фоновая задача: раз в 2 минуты проверяет, идёт ли стрим у maddyson."""
    global last_stream_id
    token = await get_kick_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Получаем информацию о канале
                ch_resp = await client.get(
                    f"https://api.kick.com/public/v1/channels?slug={KICK_CHANNEL_SLUG}",
                    headers=headers
                )
                
                if ch_resp.status_code != 200:
                    logger.warning(f"⚠️ Ошибка запроса канала: {ch_resp.status_code}")
                    await asyncio.sleep(120)
                    continue
                
                data = ch_resp.json().get("data", [])
                if not data:
                    await asyncio.sleep(120)
                    continue
                
                channel = data[0]
                # В публичном API Kick is_live может быть в разных местах, смотрим stream
                stream = channel.get("stream")
                
                if stream and stream.get("is_live"):
                    stream_id = stream.get("id")  # Уникальный ID стрима
                    
                    # Если это новый стрим (мы ещё не постили)
                    if stream_id != last_stream_id:
                        logger.info(f"🔴 [POLLING] Обнаружен стрим! ID: {stream_id}")
                        logger.info(f"   Название: {stream.get('session_title', 'Без названия')}")
                        logger.info(f"   Превью: {stream.get('thumbnail', {}).get('url', 'Нет URL')}")
                        
                        # TODO: Здесь будет вызов генерации поста и отправки в Telegram
                        # await process_new_stream(channel, stream)
                        
                        last_stream_id = stream_id
                    else:
                        logger.debug(f"⏳ Стрим {stream_id} уже обработан, пропускаем.")
                else:
                    logger.debug("⚫ [POLLING] Стрим не идёт.")
                    # Если стрим закончился, сбрасываем last_stream_id, 
                    # чтобы следующий стрим с новым ID был обработан
                    if last_stream_id is not None:
                        logger.info("⚫ Стрим закончился, ждём следующий.")
                        last_stream_id = None
                        
        except Exception as e:
            logger.error(f"❌ Ошибка в polling: {e}")
        
        await asyncio.sleep(120)  # Ждём 2 минуты

@app.on_event("startup")
async def startup_event():
    # Подписка на вебхуки (как было)
    await subscribe_to_kick_events()
    # Запускаем polling в фоне
    asyncio.create_task(check_stream_status())
    logger.info("🚀 Polling запущен (проверка каждые 2 минуты).")

# ... остальные маршруты и subscribe_to_kick_events() ...
