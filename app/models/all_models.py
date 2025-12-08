from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
# Alterado: Removido func.now() e adicionado now_br do módulo timezone
# func.now() é executado pelo banco (UTC), now_br é executado pelo Python (Brasília -3)
from app.core.database import Base
from app.core.timezone import now_br

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    is_client = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    is_compliant = Column(Boolean, default=True) # Adimplente
    # Alterado: DateTime SEM timezone para armazenar horário local de Brasília diretamente
    created_at = Column(DateTime, default=now_br)

class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    message_text = Column(String, nullable=True) # Pergunta do Usuário
    response_text = Column(String, nullable=True) # Resposta da IA
    sent_by_user = Column(Boolean, default=True)
    
    # Alterado: DateTime SEM timezone para armazenar horário local de Brasília diretamente
    timestamp = Column(DateTime, default=now_br)
    message_type = Column(String, nullable=True) 
    media_data = Column(String, nullable=True) 
    evolution_id = Column(String, nullable=True)

class RequestQueue(Base):
    __tablename__ = "request_queue"

    id = Column(Integer, primary_key=True, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending", index=True)
    # Alterado: DateTime SEM timezone para armazenar horário local de Brasília diretamente
    created_at = Column(DateTime, default=now_br)
    updated_at = Column(DateTime, onupdate=now_br)
    attempts = Column(Integer, default=0)

class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    queue_id = Column(Integer, ForeignKey("request_queue.id"))
    step = Column(String)
    status = Column(String) # 'success', 'error'
    details = Column(String, nullable=True)
    # Alterado: DateTime SEM timezone para armazenar horário local de Brasília diretamente
    timestamp = Column(DateTime, default=now_br)
