import os
import uvicorn
import logging
from fastapi import FastAPI

from config import check_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

check_config()

app = FastAPI(title="Kick Alert Bot")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/kick-webhook")
async def test_webhook():
    logger.info("📥 Получен запрос от Kick (тестовый режим)")
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "alive"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    logger.info(f"🚀 Запуск сервера на порту {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
