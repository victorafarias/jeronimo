from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.queue_service import add_to_queue
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook/evolution")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
        logger.info(f"Webhook recebido: {payload}")
        
        # O payload da Evolution vem como uma lista normalmente
        if isinstance(payload, list):
            logger.info("Processando lista de mensagens...")
            for message in payload:
                item = add_to_queue(db, message)
                if item:
                     logger.info(f"Item salvo na fila com ID: {item.id}")
                else:
                     logger.warning("Item ignorado (evento incorreto?)")
        else:
            logger.info("Processando mensagem única...")
            item = add_to_queue(db, payload)
            if item:
                 logger.info(f"Item salvo na fila com ID: {item.id}")
            else:
                 logger.warning("Item ignorado (evento incorreto?)")
            
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
