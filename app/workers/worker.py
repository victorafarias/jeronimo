import logging
import time
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.all_models import RequestQueue, ProcessingLog

logger = logging.getLogger("Worker")

def log_step(db: Session, queue_id: int, step: str, status: str, details: str = None):
    new_log = ProcessingLog(
        queue_id=queue_id,
        step=step,
        status=status,
        details=details
    )
    db.add(new_log)
    db.commit()

def process_request(queue_id: int):
    # Cria uma nova sessão para esta thread
    db = SessionLocal()
    try:
        item = db.query(RequestQueue).filter(RequestQueue.id == queue_id).first()
        if not item:
            logger.error(f"Item {queue_id} não encontrado para processamento.")
            return

        logger.info(f"Iniciando processamento do item {queue_id}")
        log_step(db, queue_id, "START", "success", "Iniciando fluxo do agente")

        # Payload disponível em item.payload
        # Extrair dados do payload (Evolution API v2 structure)
        # Exemplo: body -> data -> message -> conversation (texto) ou audioMessage
        # Payload disponível em item.payload
        payload = item.payload
        
        # Tenta pegar 'data' de 'body' ou da raiz
        body = payload.get("body", {})
        data = body.get("data")
        
        if not data:
            data = payload.get("data", {})
            
        key = data.get("key", {})
        remote_jid = key.get("remoteJid", "")
        if not remote_jid:
            logger.error("Não foi possível identificar remoteJid")
            log_step(db, queue_id, "EXTRACT", "error", "RemoteJid não encontrado")
            item.status = "failed"
            db.commit()
            return
            
        phone = remote_jid.split("@")[0]
        push_name = data.get("pushName", "Desconhecido")
        
        # Extrair dados básicos para log
        evo_id = key.get("id")
        
        # Extrair mensagem
        msg_obj = data.get("message", {})
        message_type = data.get("messageType", "text") # default text
        
        # Mapeamento básico de tipos aceitos
        # Texto pode vir como "conversation" ou "extendedTextMessage"
        # Audio como "audioMessage"
        
        is_text = "conversation" in msg_obj or "extendedTextMessage" in msg_obj
        is_audio = "audioMessage" in msg_obj
        
        # (*Melhoria) 1. Verifica no json da requisição o tipo de mensagem enviada
        if not (is_text or is_audio):
            logger.info(f"Tipo de mensagem não suportado: {message_type}")
            send_message(phone, "Desculpe, no momento só consigo processar mensagens de texto e áudio.")
            log_step(db, queue_id, "TYPE_CHECK", "stopped", f"Tipo não suportado: {message_type}")
            item.status = "completed"
            db.commit()
            return
            
        message_text = msg_obj.get("conversation") or \
                       msg_obj.get("extendedTextMessage", {}).get("text") or \
                       ""
        
        media_data = None
        if is_audio:
             if not message_text:
                message_text = "[ÁUDIO RECEBIDO]" # Placeholder para log
             
             # Tentar extrair base64 do payload (requer configuração includeBase64OnData na Evolution)
             audio_msg = msg_obj.get("audioMessage", {})
             # Evolution v2 as vezes manda direto ou pode precisar de fetch. O usuario pediu para enviar base64.
             # Vamos tentar pegar 'base64' (comum em algumas versoes) ou verificar se há necessidade de download.
             # Por hora, assumindo que vem no payload conforme padrao de webhook full
             media_data = audio_msg.get("base64") 
             
             if not media_data:
                 logger.warning("Base64 de áudio não encontrado no payload. Verifique cfg da Evolution.")

        if not message_text and not is_audio:
            logger.warning("Mensagem vazia ou tipo não suportado.")
            log_step(db, queue_id, "EXTRACT", "skipped", "Mensagem sem texto")
            item.status = "completed"
            db.commit()
            return

        from app.services.flow_service import (
            get_or_create_user, 
            process_lead_logic, 
            check_block_and_compliant, 
            get_chat_context, 
            save_chat_log
        )
        from app.services.evolution_service import send_message
        from app.services.ai_service import process_with_n8n

        # Passo 1
        log_step(db, queue_id, "STEP_1", "processing", "Identificando usuário")
        user = get_or_create_user(db, phone, push_name)
        
        # Loga a mensagem do usuário (COM NOVOS CAMPOS)
        user_msg_log = save_chat_log(db, phone, message_text, "user", 
                                     message_type=message_type, 
                                     media_data=media_data, 
                                     evolution_id=evo_id)

        if not user.is_client:
            # Lógica de Lead
            should_continue = process_lead_logic(db, user, message_text)
            if not should_continue:
                log_step(db, queue_id, "LEAD_RULE", "stopped", "Regra de lead interrompeu fluxo")
                item.status = "completed"
                db.commit()
                return

        # Passo 2 e 3 (Bloqueio e Adimplência)
        if not check_block_and_compliant(db, user):
            log_step(db, queue_id, "BLOCK_RULE", "stopped", "Usuário bloqueado ou inadimplente")
            item.status = "completed"
            db.commit()
            return
            
        # Passo 4
        # Excluir a mensagem atual do contexto para não duplicar no prompt
        context = get_chat_context(db, phone, exclude_message_id=user_msg_log.id)
        
        # Passo 5
        log_step(db, queue_id, "AI_PROCESS", "processing", "Enviando para n8n")
        try:
            # Enviando para n8n com novos campos
            ai_response = process_with_n8n(context, message_text, phone, 
                                           message_type=message_type, 
                                           media_data=media_data, 
                                           message_id=evo_id)
            
            if ai_response:
                # Passo 6 (Sucesso)
                # Resposta da IA sempre é texto por enquanto, e gerada pelo bot (sem evo id externo)
                save_chat_log(db, phone, ai_response, "bot", message_type="text") 
                send_message(phone, ai_response)
                log_step(db, queue_id, "RESPONSE", "success", "Resposta enviada")
                item.status = "completed"
            else:
                # Falha genérica n8n
                raise Exception("Resposta nula do n8n")
                
        except TimeoutError:
            log_step(db, queue_id, "TIMEOUT", "error", "n8n não respondeu em 60s")
            # Enviar para fila de falhas
            item.status = "failed"
            # TODO: Enviar email 
            
        except Exception as e:
            logger.error(f"Erro IA: {e}")
            log_step(db, queue_id, "AI_ERROR", "error", str(e))
            item.status = "failed"
            
        db.commit()
        
    except Exception as e:
        logger.error(f"Erro ao processar item {queue_id}: {e}")
        log_step(db, queue_id, "ERROR", "error", str(e))
        if item:
            item.status = "failed"
            db.commit()
    finally:
        db.close()
