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
                
                # Caso 1: Retorno Lista (Evolution/n8n padrão as vezes retorna lista)
                if isinstance(data, list) and len(data) > 0:
                    first_item = data[0]
                    # Tenta pegar campos estruturados se existirem
                    if isinstance(first_item, dict):
                        # Se vier estruturado com pergunta/resposta
                        if "respostaIA" in first_item:
                             return {
                                 "respostaIA": first_item.get("respostaIA"), 
                                 "perguntaUsuario": first_item.get("perguntaUsuario")
                             }
                        
                        # Fallback: Tenta extrair texto estilo Evolution message
                        msg = first_item.get("message", {})
                        text_val = None
                        if isinstance(msg, dict):
                             text_val = msg.get("conversation") or msg.get("extendedTextMessage", {}).get("text")
                        
                        if not text_val:
                             text_msg = first_item.get("textMessage", {})
                             if text_msg:
                                text_val = text_msg.get("text")
                        
                        return {"respostaIA": text_val or str(first_item), "perguntaUsuario": None}

                # Caso 2: Retorno Dict
                if isinstance(data, dict):
                    # Se tiver os campos esperados
                    if "respostaIA" in data:
                        return {
                            "respostaIA": data.get("respostaIA"),
                            "perguntaUsuario": data.get("perguntaUsuario")
                        }

                    # Formatos comuns genéricos
                    text_val = data.get("output") or data.get("text") or data.get("resposta") or \
                               data.get("message", {}).get("conversation")
                    
                    return {"respostaIA": text_val, "perguntaUsuario": None}
                           
                return {"respostaIA": response.text, "perguntaUsuario": None}
                
            except ValueError:
                return {"respostaIA": response.text, "perguntaUsuario": None}
        else:
            logger.error(f"Erro n8n: {response.status_code} - {response.text}")
            return None
            
    except httpx.TimeoutException:
        logger.error("Timeout ao aguardar resposta do n8n (60s).")
        raise TimeoutError("n8n timeout")
    except Exception as e:
        logger.error(f"Erro de conexão com n8n: {e}")
        return None
