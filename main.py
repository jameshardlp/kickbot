import os
import uvicorn
import logging
import httpx
from fastapi import FastAPI

from config import check_config, KICK_CLIENT_ID, KICK_CLIENT_SECRET, KICK_CHANNEL_SLUG
from kick_webhook import router as kick_router  # <-- Импортируем наш обработчик

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

check_config()

app = FastAPI(title="Kick Alert Bot")

# Подключаем роутер с вебхуками
app.include_router(kick_router)

# ============================================================
# Подписка на события Kick при старте
# ============================================================
async def subscribe_to_kick_events():
    # ... (код подписки остаётся без изменений) ...
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

            ch_resp = await client.get(
                f"https://api.kick.com/public/v1/channels?slug={KICK_CHANNEL_SLUG}",
                headers=headers
            )
            channels = ch_resp.json().get("data", [])
            if not channels:
                logger.error(f"❌ Канал {KICK_CHANNEL_SLUG} не найден.")
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

@app.on_event("startup")
async def startup_event():
    await subscribe_to_kick_events()

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