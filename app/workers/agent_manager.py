import time
import logging
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.all_models import RequestQueue
from app.workers.worker import process_request
import threading

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentManager")

def get_pending_count(db: Session):
    return db.query(RequestQueue).filter(RequestQueue.status == "pending").count()

def get_pending_items(db: Session, limit: int):
    return db.query(RequestQueue).filter(RequestQueue.status == "pending").order_by(RequestQueue.created_at.asc()).limit(limit).all()

def agent_manager_loop():
    logger.info("Iniciando Gerenciador de Agentes...")
    while True:
        try:
            with SessionLocal() as db:
                count = get_pending_count(db)
                
                # Regra: A cada 3 requisições, acorda um agente.
                # Se tiver 3 ou mais, processa em lotes de 3 (ou dispara workers para eles).
                if count >= 3:
                    logger.info(f"Fila atingiu {count} itens. Acordando Agente Processador...")
                    
                    # Pega os 3 mais antigos
                    items = get_pending_items(db, 3)
                    
                    for item in items:
                        # Atualiza para processing para não ser pego novamente
                        item.status = "processing"
                        db.add(item)
                    db.commit()
                    
                    # Dispara thread para processar cada um (simulando agentes independentes)
                    # Em um sistema mais robusto, isso poderia ser Celery ou RabbitMQ, 
                    # mas threading funciona bem para o escopo atual.
                    for item in items:
                        t = threading.Thread(target=process_request, args=(item.id,))
                        t.start()
                        
                else:
                    # Se tiver menos de 3, dorme um pouco para não onerar CPU
                    # Mas o requisito diz "A regra é: a cada 3 requisições...". 
                    # Isso implica que se tiver 1 ou 2, ficam parados? 
                    # Sim, "não oneramos o servidor sem necessidade".
                    # Vamos manter assim. Se o usuário quiser timeout (ex: processa se ficar muito tempo), ele pediria.
                    logger.debug(f"Fila com {count} itens. Aguardando...")
            
            time.sleep(5) # Verifica a cada 5 segundos
            
        except Exception as e:
            logger.error(f"Erro no loop do gerenciador: {e}")
            time.sleep(10)

if __name__ == "__main__":
    agent_manager_loop()
