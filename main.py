import os
import uvicorn
import logging
import httpx
from fastapi import FastAPI

from config import check_config, KICK_CLIENT_ID, KICK_CLIENT_SECRET, KICK_CHANNEL_SLUG

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

check_config()

app = FastAPI(title="Kick Alert Bot")

# ============================================================
# Подписка на события Kick при старте
# ============================================================
async def subscribe_to_kick_events():
    """
    Получает app access token, находит broadcaster_user_id по slug
    и подписывается на событие livestream.status.updated.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # 1. Получаем app access token
            logger.info("🔑 Получаем токен Kick...")
            token_resp = await client.post(
                "https://id.kick.com/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": KICK_CLIENT_ID,
                    "client_secret": KICK_CLIENT_SECRET,
                }
            )
            
            if token_resp.status_code != 200:
                logger.error(f"❌ Ошибка получения токена Kick: {token_resp.status_code} — {token_resp.text}")
                return
            
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                logger.error("❌ В ответе нет access_token")
                return
            
            logger.info("✅ Токен Kick получен.")
            headers = {"Authorization": f"Bearer {access_token}"}

            # 2. Получаем broadcaster_user_id по slug
            logger.info(f"🔍 Ищем канал {KICK_CHANNEL_SLUG} на Kick...")
            ch_resp = await client.get(
                f"https://api.kick.com/public/v1/channels?slug={KICK_CHANNEL_SLUG}",
                headers=headers
            )
            
            if ch_resp.status_code != 200:
                logger.error(f"❌ Ошибка поиска канала: {ch_resp.status_code} — {ch_resp.text}")
                return
            
            ch_data = ch_resp.json()
            # Структура ответа: {"data": [{...}], "message": "OK"}
            channels = ch_data.get("data", [])
            if not channels:
                logger.error(f"❌ Канал {KICK_CHANNEL_SLUG} не найден.")
                return
            
            broadcaster_id = channels[0].get("broadcaster_user_id")
            if not broadcaster_id:
                logger.error("❌ В ответе нет broadcaster_user_id")
                return
            
            logger.info(f"✅ Найден канал: {KICK_CHANNEL_SLUG}, broadcaster_user_id = {broadcaster_id}")

            # 3. Подписываемся на событие
            logger.info("📡 Подписываемся на livestream.status.updated...")
            sub_resp = await client.post(
                "https://api.kick.com/public/v1/events/subscriptions",
                headers=headers,
                json={
                    "broadcaster_user_id": broadcaster_id,
                    "method": "webhook",
                    "events": [
                        {"name": "livestream.status.updated", "version": 1}
                    ]
                }
            )
            
            if sub_resp.status_code in (200, 201):
                logger.info(f"✅ Подписка создана успешно: {sub_resp.text}")
            elif sub_resp.status_code == 409:
                logger.info("ℹ️ Подписка уже существует (409 Conflict).")
            else:
                logger.error(f"❌ Ошибка подписки: {sub_resp.status_code} — {sub_resp.text}")

    except Exception as e:
        logger.error(f"❌ Исключение при подписке на Kick: {e}")


@app.on_event("startup")
async def startup_event():
    """Вызывается один раз при старте сервера."""
    await subscribe_to_kick_events()


# ============================================================
# Маршруты
# ============================================================
@app.get("/")
async def root():
    return {"status": "alive"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/kick-webhook")
async def test_webhook():
    logger.info("📥 Получен запрос от Kick (тестовый режим)")
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    logger.info(f"🚀 Запуск сервера на порту {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
