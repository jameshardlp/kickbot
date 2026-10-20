import asyncio
import logging
import httpx
from config import KICK_CLIENT_ID, KICK_CLIENT_SECRET

logger = logging.getLogger(__name__)

async def get_kick_token():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://id.kick.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": KICK_CLIENT_ID,
                "client_secret": KICK_CLIENT_SECRET,
            }
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
        logger.error(f"❌ Ошибка получения токена: {resp.status_code}")
        return None

async def kick_request_with_retry(method: str, url: str, **kwargs):
    """
    Делает запрос к Kick API с обработкой 429 (Too Many Requests).
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(method, url, **kwargs)
                
                if response.status_code == 429:
                    wait_time = 2 ** attempt  # 1, 2, 4 секунды
                    logger.warning(f"⚠️ Kick API 429, ждём {wait_time} сек (попытка {attempt+1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                
                return response
        except Exception as e:
            logger.error(f"Ошибка запроса к Kick: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    
    return None