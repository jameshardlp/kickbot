import base64
import json
import logging
from fastapi import APIRouter, Request, HTTPException
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

from config import KICK_PUBLIC_KEY

logger = logging.getLogger(__name__)

# Создаем роутер FastAPI для вебхуков
router = APIRouter()

# Загружаем публичный ключ один раз при старте
public_key = serialization.load_pem_public_key(KICK_PUBLIC_KEY.encode('utf-8'))

def verify_kick_signature(message_id: str, timestamp: str, raw_body: bytes, signature_b64: str) -> bool:
    """
    Проверяет подпись вебхука от Kick.
    """
    try:
        # 1. Формируем строку для проверки: message_id.timestamp.raw_body
        payload = f"{message_id}.{timestamp}.".encode('utf-8') + raw_body
        
        # 2. Декодируем подпись из Base64
        signature = base64.b64decode(signature_b64)
        
        # 3. Проверяем подпись с помощью публичного ключа (RSA-SHA256)
        public_key.verify(
            signature,
            payload,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        logger.warning("❌ Неверная подпись вебхука!")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке подписи: {e}")
        return False

@router.post("/kick-webhook")
async def kick_webhook_handler(request: Request):
    """
    Основной обработчик POST-запросов от Kick.
    """
    # Получаем заголовки, которые присылает Kick
    message_id = request.headers.get("Kick-Event-Message-Id")
    timestamp = request.headers.get("Kick-Event-Message-Timestamp")
    signature = request.headers.get("Kick-Event-Signature")
    
    if not all([message_id, timestamp, signature]):
        logger.warning("⚠️ В запросе отсутствуют необходимые заголовки Kick.")
        raise HTTPException(status_code=400, detail="Missing Kick headers")

    # Важно: получаем сырое тело запроса (до парсинга JSON)
    raw_body = await request.body()

    # Проверяем подпись
    if not verify_kick_signature(message_id, timestamp, raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Если подпись верна, парсим JSON
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # --- Логика обработки события ---
    event_type = payload.get("type")
    logger.info(f"✅ Получен вебхук от Kick: {event_type}")

    if event_type == "livestream.status.updated":
        data = payload.get("data", {})
        is_live = data.get("is_live", False)
        
        if is_live:
            logger.info("🔴 Стрим начался! Запускаем генерацию поста...")
            
            # Здесь мы позже вызовем функцию генерации поста
            # Например: await process_new_stream(data)
            
            # ВРЕМЕННАЯ ЗАГЛУШКА:
            print(f"DEBUG: Название стрима: {data.get('title')}")
            print(f"DEBUG: Превью: {data.get('thumbnail_url')}")
            
        else:
            logger.info("⚫ Стрим закончился.")

    # Kick ожидает код 200, чтобы считать вебхук доставленным
    return {"status": "ok"}