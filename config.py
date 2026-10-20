import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Токен Telegram-бота
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ID канала или чата, куда бот будет отправлять посты
# (например, "@my_channel" или "-100123456789")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Ключ DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Данные приложения Kick
KICK_CLIENT_ID = os.getenv("KICK_CLIENT_ID")
KICK_CLIENT_SECRET = os.getenv("KICK_CLIENT_SECRET")

# Секрет для проверки подписи вебхука (Kick выдаст его, когда вы настроите вебхук)
KICK_WEBHOOK_SECRET = os.getenv("KICK_WEBHOOK_SECRET")

# ID канала на Kick, за которым мы следим (slug)
KICK_CHANNEL_SLUG = "maddyson"

def check_config():
    """Проверяет, что все критически важные переменные заданы."""
    missing = []
    if not TELEGRAM_BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHANNEL_ID: missing.append("TELEGRAM_CHANNEL_ID")
    if not DEEPSEEK_API_KEY: missing.append("DEEPSEEK_API_KEY")
    if not KICK_CLIENT_ID: missing.append("KICK_CLIENT_ID")
    if not KICK_CLIENT_SECRET: missing.append("KICK_CLIENT_SECRET")
    
    if missing:
        raise ValueError(f"Отсутствуют обязательные переменные в .env: {', '.join(missing)}")
    
    print("✅ Конфигурация успешно загружена.")