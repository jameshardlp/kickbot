import os
import uvicorn
import logging
import httpx
import asyncio
from fastapi import FastAPI

from config import check_config, TELEGRAM_BOT_TOKEN
from kick_webhook import router as kick_router
from handler import process_new_stream
from database import (
    init_db, set_user_slug, get_user_slug, get_all_users,
    set_channel_slug, get_all_channels, remove_channel,
    get_stream_state, set_stream_state
)
from kick_client import get_kick_token, kick_request_with_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

check_config()
init_db()

app = FastAPI(title="Kick Alert Bot")
app.include_router(kick_router)

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def check_stream_status():
    """Проверяет статусы для всех уникальных slug из users + channels (макс 60)."""
    while True:
        try:
            token = await get_kick_token()
            if not token:
                await asyncio.sleep(120)
                continue

            headers = {"Authorization": f"Bearer {token}"}
            
            # Собираем уникальные slug из обеих таблиц
            user_slugs = set(slug for _, slug in get_all_users())
            channel_slugs = set(slug for _, slug, _ in get_all_channels())
            all_slugs = list(user_slugs | channel_slugs)[:60]
            
            if not all_slugs:
                all_slugs = ["maddyson"]

            logger.info(f"🔍 Проверяю slug'и: {all_slugs}")

            for slug in all_slugs:
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

                                # Проверяем, не обрабатывали ли мы уже этот стрим (из БД!)
                                last_id = get_stream_state(slug)
                                if last_id != stream_id:
                                    logger.info(f"🔴 Обнаружен стрим {slug}! ID: {stream_id}")
                                    
                                    title = "Новый стрим"
                                    thumbnail_url = stream.get("thumbnail")
                                    viewers = stream.get("viewer_count", 0)
                                    
                                    # 1. Пользователи в ЛС
                                    for user_id, uslug in get_all_users():
                                        if uslug == slug:
                                            await process_new_stream(
                                                user_id, stream_id, title, thumbnail_url, viewers, slug
                                            )
                                    
                                    # 2. Каналы
                                    for chat_id, cslug, _ in get_all_channels():
                                        if cslug == slug:
                                            await process_new_stream(
                                                chat_id, stream_id, title, thumbnail_url, viewers, slug
                                            )
                                    
                                    # Сохраняем в БД!
                                    set_stream_state(slug, stream_id)
                            else:
                                # Стрим закончился — сбрасываем состояние в БД
                                if get_stream_state(slug) is not None:
                                    logger.info(f"⚫ Стрим {slug} закончился.")
                                    set_stream_state(slug, None)
                                    
                except Exception as e:
                    logger.error(f"❌ Ошибка при проверке {slug}: {e}")
                
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Ошибка в polling: {e}")
        
        await asyncio.sleep(120)

async def telegram_polling():
    """Слушает ЛС и каналы (channel_post / my_chat_member)."""
    offset = 0
    while True:
        try:
            # Увеличенный таймаут для long polling
            async with httpx.AsyncClient(timeout=httpx.Timeout(40.0, connect=10.0)) as client:
                resp = await client.get(
                    f"{TELEGRAM_API_URL}/getUpdates",
                    params={
                        "offset": offset,
                        "timeout": 30,
                        "allowed_updates": '["message", "channel_post", "my_chat_member"]'
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        
                        # my_chat_member
                        if "my_chat_member" in update:
                            mcm = update["my_chat_member"]
                            chat = mcm["chat"]
                            new_status = mcm["new_chat_member"]["status"]
                            
                            if new_status in ("administrator", "member"):
                                logger.info(f"🆕 Бот добавлен в чат: {chat.get('title', chat['id'])} ({chat['id']})")
                                set_channel_slug(chat["id"], "maddyson", chat.get("title", ""))
                                await client.post(
                                    f"{TELEGRAM_API_URL}/sendMessage",
                                    json={
                                        "chat_id": chat["id"],
                                        "text": "✅ Бот добавлен! По умолчанию отслеживаю **maddyson**.\nЧтобы сменить стримера, напиши: `/стример https://kick.com/username`"
                                    }
                                )
                            elif new_status in ("left", "kicked"):
                                logger.info(f"🚪 Бот удалён из чата: {chat['id']}")
                                remove_channel(chat["id"])
                            continue

                        # channel_post
                        if "channel_post" in update:
                            post = update["channel_post"]
                            text = post.get("text", "")
                            chat_id = post["chat"]["id"]
                            
                            if text.startswith("/стример"):
                                parts = text.split(maxsplit=1)
                                if len(parts) < 2:
                                    await client.post(
                                        f"{TELEGRAM_API_URL}/sendMessage",
                                        json={"chat_id": chat_id, "text": "❌ Укажи ссылку: /стример https://kick.com/username"}
                                    )
                                    continue
                                
                                link = parts[1].strip()
                                slug = link.split("kick.com/")[-1].strip("/") if "kick.com/" in link else link.strip("/")
                                
                                if not slug:
                                    await client.post(
                                        f"{TELEGRAM_API_URL}/sendMessage",
                                        json={"chat_id": chat_id, "text": "❌ Не удалось извлечь имя стримера."}
                                    )
                                    continue
                                
                                set_channel_slug(chat_id, slug, post["chat"].get("title", ""))
                                await client.post(
                                    f"{TELEGRAM_API_URL}/sendMessage",
                                    json={"chat_id": chat_id, "text": f"✅ Канал привязан к стримеру: {slug}"}
                                )
                            continue

                        # message (ЛС)
                        message = update.get("message")
                        if not message:
                            continue
                        
                        text = message.get("text", "")
                        chat_id = message["chat"]["id"]
                        user_id = message["from"]["id"]
                        
                        # Команда /стример
                        if text.startswith("/стример"):
                            parts = text.split(maxsplit=1)
                            if len(parts) < 2:
                                await client.post(
                                    f"{TELEGRAM_API_URL}/sendMessage",
                                    json={"chat_id": chat_id, "text": "❌ Укажи ссылку: /стример https://kick.com/username"}
                                )
                                continue
                            
                            link = parts[1].strip()
                            slug = link.split("kick.com/")[-1].strip("/") if "kick.com/" in link else link.strip("/")
                            
                            if not slug:
                                await client.post(
                                    f"{TELEGRAM_API_URL}/sendMessage",
                                    json={"chat_id": chat_id, "text": "❌ Не удалось извлечь имя стримера."}
                                )
                                continue
                            
                            set_user_slug(user_id, slug)
                            await client.post(
                                f"{TELEGRAM_API_URL}/sendMessage",
                                json={"chat_id": chat_id, "text": f"✅ Теперь отслеживаю: {slug}\n🔗 https://kick.com/{slug}"}
                            )
                        
                        # Команда /статус
                        elif text.startswith("/статус"):
                            slug = get_user_slug(user_id) or "maddyson (по умолчанию)"
                            await client.post(
                                f"{TELEGRAM_API_URL}/sendMessage",
                                json={
                                    "chat_id": chat_id,
                                    "text": f"📡 Твой стример: {slug}\n🔗 https://kick.com/{slug}"
                                }
                            )
                        
                        # Команда /сброс
                        elif text.startswith("/сброс"):
                            from database import get_stream_state, set_stream_state
                            # Сбрасываем stream_state для всех slug'ов, которые есть в базе
                            user_slugs = set(slug for _, slug in get_all_users())
                            channel_slugs = set(slug for _, slug, _ in get_all_channels())
                            all_slugs = user_slugs | channel_slugs
                            
                            for slug in all_slugs:
                                set_stream_state(slug, None)
                            
                            # Если в списке есть maddyson (дефолт), но пользователь его не выбирал — 
                            # просто сбрасываем состояние, не удаляя из базы
                            if "maddyson" in all_slugs:
                                set_stream_state("maddyson", None)
                            
                            await client.post(
                                f"{TELEGRAM_API_URL}/sendMessage",
                                json={
                                    "chat_id": chat_id,
                                    "text": f"🔄 Состояние сброшено для {len(all_slugs)} стримеров. Следующий цикл polling увидит стримы как новые."
                                }
                            )
                            logger.info(f"🔄 Пользователь {user_id} сбросил состояние стримов.")
                            
        except Exception as e:
            logger.error(f"❌ Ошибка в Telegram polling: {type(e).__name__}: {e}")
        
        await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_stream_status())
    asyncio.create_task(telegram_polling())
    logger.info("🚀 Polling запущен (users + channels + stream_state) и Telegram polling.")

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
