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
            for message in payload:
                add_to_queue(db, message)
        else:
            add_to_queue(db, payload)
            
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
