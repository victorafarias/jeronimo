from app.core.database import engine, Base
from app.models.all_models import User, Lead, ChatLog, RequestQueue, ProcessingLog
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    logger.info("Criando tabelas no banco de dados...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas criadas com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")

if __name__ == "__main__":
    init_db()
