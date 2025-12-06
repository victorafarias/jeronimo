from sqlalchemy.orm import Session
from app.models.all_models import RequestQueue
import json

def add_to_queue(db: Session, payload: dict):
    # Validar se é uma mensagem de interesse (ex: messages.upsert)
    # Segundo o payload de exemplo: "body" -> "event": "messages.upsert"
    
    body = payload.get("body", {})
    event = body.get("event")
    
    if event == "messages.upsert":
        # Extrair dados básicos para log rápido se necessário, 
        # mas aqui salvamos o payload inteiro raw para processamento pelo worker
        new_request = RequestQueue(
            payload=payload,
            status="pending"
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        return new_request
    
    return None
