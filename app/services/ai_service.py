import httpx
from app.core.config import settings
import logging

logger = logging.getLogger("AIService")

def process_with_n8n(chat_context: str, current_message: str, phone: str, user_name: str = None,
                     message_type: str = "text", media_data: str = None, message_id: str = None):
    url = settings.N8N_WEBHOOK_URL
    
    payload = {
        "log-de-conversas": chat_context,
        "pergunta-do-usuario-atual": current_message,
        "telefone-usuario": f"{phone}@s.whatsapp.net",
        "nome_usuario": user_name,
        "tipo_mensagem": message_type,
        "audio_base64": media_data, # Pode ser null se for texto
        "message_id": message_id
    }
    
    try:
        # Timeout de 60 segundos conforme requisito
        logger.info("Enviando requisição para n8n...")
        response = httpx.post(url, json=payload, timeout=60.0)
        
        if response.status_code == 200:
            try:
                data = response.json()
                logger.info(f"Resposta bruta n8n: {data}") # Debug temporário
                
                # Caso 1: Retorno complexo estilo Evolution (Lista de objetos)
                if isinstance(data, list) and len(data) > 0:
                    first_item = data[0]
                    # Tenta extrair de message.conversation
                    msg = first_item.get("message", {})
                    if isinstance(msg, dict):
                         return msg.get("conversation") or msg.get("extendedTextMessage", {}).get("text")
                         
                    # Tenta extrair textMessage.text (outro formato possível)
                    text_msg = first_item.get("textMessage", {})
                    if text_msg:
                        return text_msg.get("text")
                        
                    return str(first_item) # Fallback

                # Caso 2: Retorno simples (Dict)
                if isinstance(data, dict):
                    # Formatos comuns n8n
                    return data.get("output") or data.get("text") or data.get("resposta") or \
                           data.get("message", {}).get("conversation") # Caso venha um objeto Evolution único
                           
                return response.text # Fallback texto puro
                
            except ValueError:
                return response.text
        else:
            logger.error(f"Erro n8n: {response.status_code} - {response.text}")
            return None
            
    except httpx.TimeoutException:
        logger.error("Timeout ao aguardar resposta do n8n (60s).")
        raise TimeoutError("n8n timeout")
    except Exception as e:
        logger.error(f"Erro de conexão com n8n: {e}")
        return None
