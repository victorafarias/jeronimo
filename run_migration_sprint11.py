from app.core.database import SessionLocal
from sqlalchemy import text
import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MigrationSprint11")

def run_migration():
    logger.info("Iniciando migração (Sprint 11 - Response Text)...")
    db = SessionLocal()
    try:
        logger.info("Adicionando coluna response_text em chat_logs...")
        db.execute(text("ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS response_text TEXT;"))
        db.commit()
        logger.info("Migração concluída com sucesso!")
    except Exception as e:
        logger.error(f"Erro na migração: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
