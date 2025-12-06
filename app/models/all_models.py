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

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    interaction_count = Column(Integer, default=0)

class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_phone = Column(String, index=True) # Relacionamento lógico via telefone para facilitar
    message_text = Column(String, nullable=True)
    # Se origin for 'bot', response_text pode ser redundante se usarmos message_text,
    # mas o requisito pede "log de conversas (perguntas e respostas)".
    # Vamos estruturar: uma entrada para cada mensagem (user ou bot).
    origin = Column(String) # 'user', 'bot', 'system'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

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
