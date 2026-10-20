import uvicorn
import logging
from fastapi import FastAPI

from config import check_config
from kick_webhook import router as kick_router

# Настраиваем логирование, чтобы видеть, что происходит
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Проверяем, что все переменные окружения на месте
check_config()

# Создаем приложение FastAPI
app = FastAPI(title="Kick Alert Bot")

# Подключаем наш роутер с вебхуками
app.include_router(kick_router)

@app.get("/")
async def root():
    # Этот эндпоинт нужен, чтобы мы могли проверить, что сервер жив
    return {"status": "alive", "message": "Kick Bot is running"}

if __name__ == "__main__":
    # BotHost обычно передает порт через переменную окружения PORT
    import os
    port = int(os.getenv("PORT", 3000))
    logger.info(f"🚀 Запуск сервера на порту {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)