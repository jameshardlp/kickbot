import os
import uvicorn
import logging
import httpx
import asyncio
from fastapi import FastAPI

from config import check_config, TELEGRAM_BOT_TOKEN
from kick_webhook import router as kick_router
from handler import process_new_stream
from state import get_current_slug, set_current_slug, get_last_stream_id, set_last_stream_id
from database import init_db, set_user_slug, get_user_slug, get_unique_slugs, get_all_users
from kick_client import get_kick_token, kick_request_with_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

check_config()
init_db()

app = FastAPI(title="Kick Alert Bot")
app.include_router(kick_router)

# Глобальные переменные для защиты от дублей (по slug)
last_stream_ids = {}  # {slug: stream_id}

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def check_stream_status():
    """Фоновая задача: проверяет статусы стримов для уникальных slug'ов из БД (макс 60)."""
    while True:
        try:
            token = await get_kick_token()
            if not token:
                await asyncio.sleep(120)
                continue

            headers = {"Authorization": f"Bearer {token}"}
            
            # Получаем до 60 уникальных slug'ов из базы
            slugs = get_unique_slugs(limit=60)
            
            # Если база пуста (новый бот), проверяем дефолтного maddyson
            if not slugs:
                slugs = ["maddyson"]

            for slug in slugs:
                try:
                    resp = await kick_request_with_retry(
                        "GET",
                        f"https://api.kick.com/public/v1/channels?slug={slug}",
                        headers=headers
                    )
                    
                    if resp and resp.status_code == 200:
                        data = resp.json().get("data", [])
                        if data:
                            channel = data[0]
                            stream = channel.get("stream")
                            
                            if stream and stream.get("is_live"):
                                stream_id = stream.get("start_time")
                                
                                if not stream_id:
                                    continue

                                # Проверяем, не обрабатывали ли мы уже этот стрим для этого slug
                                if last_stream_ids.get(slug) != stream_id:
                                    logger.info(f"🔴 [POLLING] Обнаружен стрим! ID: {stream_id} (канал: {slug})")
                                    
                                    title = "Новый стрим"
                                    thumbnail_url = stream.get("thumbnail")
                                    viewers = stream.get("viewer_count", 0)
                                    
                                    # Находим всех пользователей, которые следят за этим slug
                                    all_users = get_all_users()
                                    users_to_notify = [uid for uid, uslug in all_users if uslug == slug]
                                    
                                    if users_to_notify:
                                        # Отправляем пост каждому (в реальности здесь нужно слать в ЛС, 
                                        # но пока у нас нет chat_id в базе, поэтому шлем в общий канал)
                                        await process_new_stream(stream_id, title, thumbnail_url, viewers)
                                    else:
                                        # Если никто не следит, но это дефолтный maddyson, шлем в общий канал
                                        if slug == "maddyson":
                                            await process_new_stream(stream_id, title, thumbnail_url, viewers)
                                    
                                    last_stream_ids[slug] = stream_id
                                    set_last_stream_id(stream_id)
                            else:
                                if last_stream_ids.get(slug) is not None:
                                    logger.info(f"⚫ Стрим {slug} закончился.")
                                    last_stream_ids[slug] = None
                                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при проверке {slug}: {e}")
                
                # Небольшая пауза между запросами к разным стримерам, чтобы не долбить API
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Ошибка в polling: {e}")
        
        await asyncio.sleep(120)  # Ждём 2 минуты перед следующим циклом

async def subscribe_to_kick_events():
    """Подписка на события Kick (вебхук) для текущего канала."""
    try:
        token = await get_kick_token()
        if not token:
            return
            
        headers = {"Authorization": f"Bearer {token}"}
        slug = get_current_slug()
        
        resp = await kick_request_with_retry(
            "GET",
            f"https://api.kick.com/public/v1/channels?slug={slug}",
            headers=headers
        )
        
        if resp and resp.status_code == 200:
            channels = resp.json().get("data", [])
            if not channels:
                logger.error(f"❌ Канал {slug} не найден.")
                return
            broadcaster_id = channels[0].get("broadcaster_user_id")
            
            sub_resp = await kick_request_with_retry(
                "POST",
                "https://api.kick.com/public/v1/events/subscriptions",
                headers=headers,
                json={
                    "broadcaster_user_id": broadcaster_id,
                    "method": "webhook",
                    "events": [{"name": "livestream.status.updated", "version": 1}]
                }
            )
            
            if sub_resp and sub_resp.status_code in (200, 201):
                logger.info(f"✅ Подписка активна для {slug}: {sub_resp.text}")
            elif sub_resp and sub_resp.status_code == 409:
                logger.info(f"ℹ️ Подписка для {slug} уже существует.")
            else:
                logger.error(f"❌ Ошибка подписки: {sub_resp.status_code if sub_resp else 'None'}")
    except Exception as e:
        logger.error(f"❌ Исключение при подписке: {e}")

async def telegram_polling():
    """Слушает команды от пользователей в ЛС."""
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
                        user_id = message["from"]["id"]
                        
                        # Команда /стример <ссылка>
                        if text.startswith("/стример"):
                            parts = text.split(maxsplit=1)
                            if len(parts) < 2:
                                await client.post(
                                    f"{TELEGRAM_API_URL}/sendMessage",
                                    json={"chat_id": chat_id, "text": "❌ Укажи ссылку: /стример https://kick.com/username"}
                                )
                                continue
                            
                            link = parts[1].strip()
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
                            
                            # Сохраняем в базу
                            set_user_slug(user_id, slug)
                            
                            await client.post(
                                f"{TELEGRAM_API_URL}/sendMessage",
                                json={"chat_id": chat_id, "text": f"✅ Теперь отслеживаю канал: {slug}\nСсылка: https://kick.com/{slug}"}
                            )
                            logger.info(f"🔄 Пользователь {user_id} сменил стримера на: {slug}")
                            
                            # Переподписываемся на вебхуки (если это текущий глобальный канал)
                            set_current_slug(slug)
                            await subscribe_to_kick_events()
                        
                        # Команда /статус
                        elif text.startswith("/статус"):
                            slug = get_user_slug(user_id) or "maddyson (по умолчанию)"
                            await client.post(
                                f"{TELEGRAM_API_URL}/sendMessage",
                                json={
                                    "chat_id": chat_id,
                                    "text": f"📡 Твой текущий канал: {slug}\n🔗 https://kick.com/{slug}"
                                }
                            )
                            
        except Exception as e:
            logger.error(f"❌ Ошибка в Telegram polling: {e}")
        
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    await subscribe_to_kick_events()
    asyncio.create_task(check_stream_status())
    asyncio.create_task(telegram_polling())
    logger.info("🚀 Polling запущен (макс 60 уникальных стримеров) и Telegram polling.")

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
