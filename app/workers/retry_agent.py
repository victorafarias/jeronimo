import time
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.all_models import RequestQueue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RetryAgent")

def retry_failures():
    logger.info("Iniciando Agente de Reprocessamento...")
    while True:
        try:
            with SessionLocal() as db:
                # Busca itens falhados com menos de 3 tentativas
                failures = db.query(RequestQueue).filter(
                    RequestQueue.status == "failed",
                    RequestQueue.attempts < 3
                ).all()
                
                if failures:
                    logger.info(f"Encontrados {len(failures)} itens para reprocessar.")
                    for item in failures:
                        logger.info(f"Reenfileirando item {item.id} (Tentativa {item.attempts + 1})")
                        item.status = "pending"
                        item.attempts += 1
                        db.add(item)
                    db.commit()
                else:
                    logger.debug("Nenhuma falha recuperável encontrada.")
                    
            # Dorme 2 minutos (120s)
            time.sleep(120)
            
        except Exception as e:
            logger.error(f"Erro no agente de retry: {e}")
            time.sleep(60)

if __name__ == "__main__":
    retry_failures()
