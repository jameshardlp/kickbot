import base64
import json
import logging
from fastapi import APIRouter, Request, HTTPException
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

from config import KICK_PUBLIC_KEY

logger = logging.getLogger(__name__)

router = APIRouter()

# Загружаем публичный ключ один раз при старте
public_key = serialization.load_pem_public_key(KICK_PUBLIC_KEY.encode('utf-8'))

def verify_kick_signature(message_id: str, timestamp: str, raw_body: bytes, signature_b64: str) -> bool:
    """
    Проверяет подпись вебхука от Kick (RSA-SHA256).
    Строка для проверки: {message_id}.{timestamp}.{raw_body}
    """
    try:
        payload = f"{message_id}.{timestamp}.".encode('utf-8') + raw_body
        signature = base64.b64decode(signature_b64)
        
        public_key.verify(
            signature,
            payload,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        logger.warning("❌ Неверная подпись вебхука! Запрос отклонён.")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке подписи: {e}")
        return False

@router.post("/kick-webhook")
async def kick_webhook_handler(request: Request):
    # Получаем заголовки, которые присылает Kick
    message_id = request.headers.get("Kick-Event-Message-Id")
    timestamp = request.headers.get("Kick-Event-Message-Timestamp")
    signature = request.headers.get("Kick-Event-Signature")
    
    if not all([message_id, timestamp, signature]):
        logger.warning("⚠️ В запросе отсутствуют заголовки Kick.")
        raise HTTPException(status_code=400, detail="Missing Kick headers")

    # Получаем сырое тело запроса (до парсинга JSON)
    raw_body = await request.body()

    # Проверяем подпись
    if not verify_kick_signature(message_id, timestamp, raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Парсим JSON
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("type")
    logger.info(f"✅ Получен вебхук от Kick: {event_type}")

    if event_type == "livestream.status.updated":
        data = payload.get("data", {})
        is_live = data.get("is_live", False)
        
        if is_live:
            logger.info("🔴 Стрим начался! Данные:")
            logger.info(f"   Название: {data.get('title')}")
            logger.info(f"   Превью: {data.get('thumbnail_url')}")
            
            # Здесь позже будет вызов генерации и отправки в Telegram
            # await process_new_stream(data)
            
        else:
            logger.info("⚫ Стрим закончился.")

    return {"status": "ok"}