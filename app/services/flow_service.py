from sqlalchemy.orm import Session
from app.models.all_models import User, Lead, ChatLog
from app.services.evolution_service import send_message
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("UserFlow")

def get_or_create_user(db: Session, phone: str, push_name: str):
    user = db.query(User).filter(User.phone == phone).first()
    
    if not user:
        # Verifica se já existe na tabela de leads
        lead = db.query(Lead).filter(Lead.phone == phone).first()
        
        if not lead:
             # Grava dados na tabela de lead se não for cliente e não existir ainda
             new_lead = Lead(phone=phone)
             db.add(new_lead)
             db.commit()
             
        user = User(phone=phone, name=push_name, is_client=False) # Default não cliente
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def process_lead_logic(db: Session, user: User, message_text: str):
    # Regra: Lead tem limite de 3 respostas da IA.
    
    bot_responses = db.query(ChatLog).filter(
        ChatLog.user_phone == user.phone, 
        ChatLog.origin == 'bot'
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

def get_chat_context(db: Session, user_phone: str):
    # Passo 4: Conversas nos últimos 30 min
    limit_time = datetime.now() - timedelta(minutes=30)
    
    logs = db.query(ChatLog).filter(
        ChatLog.user_phone == user_phone,
        ChatLog.timestamp >= limit_time
    ).order_by(ChatLog.timestamp.asc()).all()
    
    if not logs:
        return ""
        
    formatted = ""
    for log in logs:
        if log.origin == 'user':
            formatted += f"Usuário: {log.message_text}\n"
        elif log.origin == 'bot':
            formatted += f"Resposta da IA: {log.message_text}\n\n"
            
    return formatted

def save_chat_log(db: Session, phone: str, text: str, origin: str):
    log = ChatLog(user_phone=phone, message_text=text, origin=origin)
    db.add(log)
    db.commit()
