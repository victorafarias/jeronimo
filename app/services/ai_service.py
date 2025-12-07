import httpx
from app.core.config import settings
import logging

logger = logging.getLogger("AIService")

def process_with_n8n(chat_context: str, current_message: str, phone: str, 
                     message_type: str = "text", media_data: str = None, message_id: str = None):
    url = settings.N8N_WEBHOOK_URL
    
    payload = {
        "log-de-conversas": chat_context,
        "pergunta-do-usuario-atual": current_message,
        "telefone-usuario": f"{phone}@s.whatsapp.net",
        "tipo_mensagem": message_type,
        "audio_base64": media_data, # Pode ser null se for texto
        "message_id": message_id
    }
    
    try:
        # Timeout de 60 segundos conforme requisito
        logger.info("Enviando requisição para n8n...")
        response = httpx.post(url, json=payload, timeout=60.0)
        
        if response.status_code == 200:
            # Assumindo que o n8n retorna JSON com campo 'resposta' ou 'text'
            # Se retornar texto puro, pegamos .text
            data = response.json()
            # Ajuste conforme o output real do n8n
            return data.get("output") or data.get("text") or data.get("resposta") or response.text
        else:
            logger.error(f"Erro n8n: {response.status_code} - {response.text}")
            return None
            
    except httpx.TimeoutException:
        logger.error("Timeout ao aguardar resposta do n8n (60s).")
        raise TimeoutError("n8n timeout")
    except Exception as e:
        logger.error(f"Erro de conexão com n8n: {e}")
        return None
