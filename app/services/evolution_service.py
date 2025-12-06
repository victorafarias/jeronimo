import httpx
from app.core.config import settings
import logging

logger = logging.getLogger("EvolutionService")

def send_message(phone: str, text: str):
    url = f"{settings.EVOLUTION_API_URL}/message/sendText/{settings.EVOLUTION_INSTANCE_NAME}"
    headers = {
        "apikey": settings.EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "number": phone,
        "options": {
            "delay": 1200,
            "presence": "composing",
            "linkPreview": False
        },
        "textMessage": {
            "text": text
        }
    }
    
    try:
        # Importante: Como chamaremos isso dentro de threads, podemos usar httpx.post síncrono ou assíncrono.
        # Por simplicidade e compatibilidade com o worker atual (threading), usarei síncrono.
        response = httpx.post(url, headers=headers, json=body, timeout=10.0)
        logger.info(f"Mensagem enviada para {phone}: Status {response.status_code}")
        if response.status_code != 201:
            logger.error(f"Erro no envio Evolution: {response.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"Exceção ao enviar mensagem Evolution: {e}")
        return False
