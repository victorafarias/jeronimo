from app.core.database import SessionLocal
from sqlalchemy import text
import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration")

def run_migration():
    logger.info("Iniciando migração manual (Sprint 9)...")
    
    commands = [
        "ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS message_type VARCHAR;",
        "ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS media_data TEXT;",
        "ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS evolution_id VARCHAR;"
    ]
    
    db = SessionLocal()
    try:
        for cmd in commands:
            logger.info(f"Executando: {cmd}")
            db.execute(text(cmd))
        db.commit()
        logger.info("Migração concluída com sucesso!")
    except Exception as e:
        logger.error(f"Erro na migração: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
