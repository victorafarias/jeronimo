from sqlalchemy.orm import Session
from app.models.all_models import User, ChatLog
from app.services.evolution_service import send_message
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("UserFlow")

def get_or_create_user(db: Session, phone: str, push_name: str):
    user = db.query(User).filter(User.phone == phone).first()
    
    if not user:
        # Cria usuário direto (conceito de Lead está implícito em is_client=False)
        user = User(phone=phone, name=push_name, is_client=False)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Atualiza nome se vier diferente e não tiver nome salvo?
        # Por enquanto mantemos o original ou atualizamos. Vamos atualizar se o push_name vier.
        if push_name and user.name != push_name:
            user.name = push_name
            db.commit()
            
    return user

def process_lead_logic(db: Session, user: User, message_text: str):
    # Regra: Lead tem limite de 3 respostas da IA.
    
    bot_responses = db.query(ChatLog).filter(
        ChatLog.user_id == user.id, 
        ChatLog.sent_by_user == False
    ).count()
    
    # Se JÁ TIVER 3 ou mais respostas, bloqueia.
    if bot_responses >= 3:
        send_message(user.phone, "Você atingiu o limite de interações gratuitas. Por favor aguarde um atendente.")
        return False # Interrompe fluxo
    else:
        return True # Segue fluxo

def check_block_and_compliant(db: Session, user: User):
    # Passo 2
    if user.is_blocked:
        send_message(user.phone, "Atendimento indisponível temporariamente. (Bloqueio)")
        return False
        
    # Passo 3
    if not user.is_compliant:
        send_message(user.phone, "Identificamos uma pendência. Entre em contato com o financeiro.")
        return False
        
    return True

def get_chat_context(db: Session, user_id: int, exclude_message_id: int = None):
    # Passo 4: Conversas nos últimos 30 min
    limit_time = datetime.now() - timedelta(minutes=30)
    
    query = db.query(ChatLog).filter(
        ChatLog.user_id == user_id,
        ChatLog.timestamp >= limit_time
    )
    
    # Exclui a mensagem atual do contexto (pois ela vai em 'pergunta-do-usuario-atual')
    if exclude_message_id:
        query = query.filter(ChatLog.id != exclude_message_id)
        
    logs = query.order_by(ChatLog.timestamp.asc()).all()
    
    if not logs:
        return ""
        
    formatted = ""
    for log in logs:
        # Formato: Pergunta + Resposta (se houver)
        if log.message_text:
            formatted += f"Usuário: {log.message_text}\n"
        
        if log.response_text:
            formatted += f"Resposta da IA: {log.response_text}\n\n"
            
    return formatted

def save_chat_log(db: Session, user_id: int, text: str, sent_by_user: bool = True, 
                  message_type: str = "text", media_data: str = None, evolution_id: str = None):
    log = ChatLog(
        user_id=user_id, 
        message_text=text, 
        sent_by_user=sent_by_user,
        message_type=message_type,
        media_data=media_data,
        evolution_id=evolution_id
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def update_chat_log_with_response(db: Session, log_id: int, response: str, transcription: str = None):
    log = db.query(ChatLog).filter(ChatLog.id == log_id).first()
    if log:
        log.response_text = response
        if transcription:
            log.message_text = transcription
        db.commit()
        db.refresh(log)
    return log
