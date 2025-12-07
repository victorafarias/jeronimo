from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    is_client = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    is_compliant = Column(Boolean, default=True) # Adimplente
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True) # Nullable temporário para migração, depois poderia ser False
    message_text = Column(String, nullable=True) # Pergunta do Usuário
    response_text = Column(String, nullable=True) # Resposta da IA
    sent_by_user = Column(Boolean, default=True) # Geralmente True agora, pois user inicia. Se False, foi bot proativo (not supported yet).
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    message_type = Column(String, nullable=True) 
    media_data = Column(String, nullable=True) 
    evolution_id = Column(String, nullable=True)

class RequestQueue(Base):
    __tablename__ = "request_queue"

    id = Column(Integer, primary_key=True, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending", index=True) # pending, processing, failed, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    attempts = Column(Integer, default=0)

class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    queue_id = Column(Integer, ForeignKey("request_queue.id"))
    step = Column(String)
    status = Column(String) # 'success', 'error'
    details = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
