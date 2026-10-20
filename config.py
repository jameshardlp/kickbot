import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Токен Telegram-бота
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ID канала или чата, куда бот будет отправлять посты
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Ключ DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Данные приложения Kick
KICK_CLIENT_ID = os.getenv("KICK_CLIENT_ID")
KICK_CLIENT_SECRET = os.getenv("KICK_CLIENT_SECRET")

# ID канала на Kick, за которым мы следим (slug)
KICK_CHANNEL_SLUG = "maddyson"

# Публичный ключ Kick для проверки подписи вебхуков (RSA)
KICK_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0C0tthITvk/EjIxCGCko
YrxM7eqP4GDnUyP4BnfgJ9yaHqniNfraxTKeRv7TGkOOZviow2zcx/YP9waURfHd
cZOHU+EKA3lSFdMpezLiDGaym+FxR0iXAFZXE9VBdCCOyBeK81/m3mGScGVBNumt
6pGCZYU9DCn5oqnC6RC5pUnlHnJp+TOXW6z8Silr4Y81a/66b0FAJ6EGUVXmXXgP
FXQRTmJcLM4EgCXfNXLwExzr2MtowBwp5PYD6Usl7uZcnMIPutPdXJ0JnvqrztFC
QTvrGMxzKLKLcKQTG159jfHGJ4wKSeenvwXN8jaVJAtW7wRAooRRT8Kho7Axe8jp
qQIDAQAB
-----END PUBLIC KEY-----"""

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
