import os
import uvicorn
import logging
import httpx
import asyncio
from fastapi import FastAPI

from config import check_config, KICK_CLIENT_ID, KICK_CLIENT_SECRET, TELEGRAM_BOT_TOKEN
from kick_webhook import router as kick_router
from handler import process_new_stream
from state import get_current_slug, set_current_slug

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

check_config()

app = FastAPI(title="Kick Alert Bot")
app.include_router(kick_router)

# Глобальная переменная для отслеживания последнего обработанного стрима
last_stream_id = None
# Глобальная переменная для текущего отслеживаемого канала
current_slug = get_current_slug()

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

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
    """Фоновая задача: проверяет статус стрима раз в 2 минуты."""
    global last_stream_id, current_slug
    token = await get_kick_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    while True:
        try:
            # Каждый раз получаем актуальный slug (мог измениться через команду)
            current_slug = get_current_slug()
            
            async with httpx.AsyncClient(timeout=30) as client:
                ch_resp = await client.get(
                    f"https://api.kick.com/public/v1/channels?slug={current_slug}",
                    headers=headers
                )
                
                if ch_resp.status_code == 200:
                    data = ch_resp.json().get("data", [])
                    if data:
                        channel = data[0]
                        stream = channel.get("stream")
                        
                        if stream and stream.get("is_live"):
                            # Используем start_time как уникальный ID стрима
                            stream_id = stream.get("start_time")
                            
                            if not stream_id:
                                logger.warning("⚠️ Не удалось определить ID стрима (нет start_time).")
                                await asyncio.sleep(120)
                                continue

                            if stream_id != last_stream_id:
                                logger.info(f"🔴 [POLLING] Обнаружен стрим! ID: {stream_id} (канал: {current_slug})")
                                
                                # Названия в этом ответе нет, используем заглушку
                                title = "Новый стрим"
                                
                                # Превью лежит прямо в stream["thumbnail"] как строка
                                thumbnail_url = stream.get("thumbnail")
                                viewers = stream.get("viewer_count", 0)
                                
                                await process_new_stream(stream_id, title, thumbnail_url, viewers)
                                
                                last_stream_id = stream_id
                        else:
                            if last_stream_id is not None:
                                logger.info("⚫ Стрим закончился. Ждём следующий.")
                                last_stream_id = None
                                
        except Exception as e:
            logger.error(f"❌ Ошибка в polling: {e}")
        
        await asyncio.sleep(120)  # Ждём 2 минуты

async def subscribe_to_kick_events():
    """Подписка на события Kick (вебхук)."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            token_resp = await client.post(
                "https://id.kick.com/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": KICK_CLIENT_ID,
                    "client_secret": KICK_CLIENT_SECRET,
                }
            )
            if token_resp.status_code != 200:
                logger.error(f"❌ Ошибка получения токена Kick: {token_resp.status_code}")
                return
            access_token = token_resp.json().get("access_token")
            headers = {"Authorization": f"Bearer {access_token}"}

            # Используем актуальный slug
            slug = get_current_slug()
            ch_resp = await client.get(
                f"https://api.kick.com/public/v1/channels?slug={slug}",
                headers=headers
            )
            channels = ch_resp.json().get("data", [])
            if not channels:
                logger.error(f"❌ Канал {slug} не найден.")
                return
            broadcaster_id = channels[0].get("broadcaster_user_id")
            
            sub_resp = await client.post(
                "https://api.kick.com/public/v1/events/subscriptions",
                headers=headers,
                json={
                    "broadcaster_user_id": broadcaster_id,
                    "method": "webhook",
                    "events": [{"name": "livestream.status.updated", "version": 1}]
                }
            )
            if sub_resp.status_code in (200, 201):
                logger.info(f"✅ Подписка активна: {sub_resp.text}")
            elif sub_resp.status_code == 409:
                logger.info("ℹ️ Подписка уже существует.")
            else:
                logger.error(f"❌ Ошибка подписки: {sub_resp.status_code} — {sub_resp.text}")
    except Exception as e:
        logger.error(f"❌ Исключение при подписке: {e}")

async def telegram_polling():
    """Фоновая задача: слушает команды от пользователя в ЛС."""
    offset = 0
    while True:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{TELEGRAM_API_URL}/getUpdates",
                    params={"offset": offset, "timeout": 30}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        message = update.get("message")
                        if not message:
                            continue
                        
                        text = message.get("text", "")
                        chat_id = message["chat"]["id"]
                        
                        # Обработка команды /стример <ссылка>
                        if text.startswith("/стример"):
                            parts = text.split(maxsplit=1)
                            if len(parts) < 2:
                                await client.post(
                                    f"{TELEGRAM_API_URL}/sendMessage",
                                    json={"chat_id": chat_id, "text": "❌ Укажи ссылку: /стример https://kick.com/username"}
                                )
                                continue
                            
                            link = parts[1].strip()
                            # Извлекаем slug из ссылки
                            if "kick.com/" in link:
                                slug = link.split("kick.com/")[-1].strip("/")
                            else:
                                slug = link.strip("/")
                            
                            if not slug:
                                await client.post(
                                    f"{TELEGRAM_API_URL}/sendMessage",
                                    json={"chat_id": chat_id, "text": "❌ Не удалось извлечь имя стримера из ссылки."}
                                )
                                continue
                            
                            set_current_slug(slug)
                            await client.post(
                                f"{TELEGRAM_API_URL}/sendMessage",
                                json={"chat_id": chat_id, "text": f"✅ Теперь отслеживаю канал: {slug}"}
                            )
                            logger.info(f"🔄 Пользователь сменил стримера на: {slug}")
                            
                            # Переподписываемся на события нового канала
                            await subscribe_to_kick_events()
                            
        except Exception as e:
            logger.error(f"❌ Ошибка в Telegram polling: {e}")
        
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    await subscribe_to_kick_events()
    asyncio.create_task(check_stream_status())
    asyncio.create_task(telegram_polling())
    logger.info("🚀 Polling запущен (проверка каждые 2 минуты) и Telegram polling.")

@app.get("/")
async def root():
    return {"status": "alive"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    logger.info(f"🚀 Запуск сервера на порту {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
