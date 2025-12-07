from app.core.database import SessionLocal
from sqlalchemy import text
import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MigrationSprint10")

def run_migration():
    logger.info("Iniciando migração complexa (Sprint 10)...")
    db = SessionLocal()
    
    try:
        # 1. Adicionar novas colunas em ChatLog
        logger.info("1. Adicionando novas colunas (user_id, sent_by_user)...")
        db.execute(text("ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id);"))
        db.execute(text("ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS sent_by_user BOOLEAN DEFAULT TRUE;"))
        db.commit()
        
        # 2. Migração de Dados: Preencher user_id baseado no user_phone antigo
        logger.info("2. Migrando dados (Vinculando logs aos usuários)...")
        
        # SQL puro para update com join (Postgres syntax)
        update_query = """
        UPDATE chat_logs
        SET user_id = users.id
        FROM users
        WHERE chat_logs.user_phone = users.phone;
        """
        db.execute(text(update_query))
        db.commit()
        
        # 3. Migrar 'origin' para 'sent_by_user'
        logger.info("3. Migrando origin para sent_by_user...")
        # Se origin era 'bot', sent_by_user = False. Se 'user', True.
        db.execute(text("UPDATE chat_logs SET sent_by_user = false WHERE origin = 'bot';"))
        db.execute(text("UPDATE chat_logs SET sent_by_user = true WHERE origin != 'bot';"))
        db.commit()
        
        # 4. Remover colunas antigas e tabela Leads
        logger.info("4. Limpeza (Dropando colunas antigas e tabela leads)...")
        
        # Drop Leads
        db.execute(text("DROP TABLE IF EXISTS leads;"))
        
        # Drop colunas antigas de ChatLog
        # Nota: Só drop se a migração deu certo (user_id não nulo). 
        # Por segurança, vamos dropar.
        db.execute(text("ALTER TABLE chat_logs DROP COLUMN IF EXISTS user_phone;"))
        db.execute(text("ALTER TABLE chat_logs DROP COLUMN IF EXISTS origin;"))
        
        db.commit()
        logger.info("Migração concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro na migração: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
