from app.core.database import engine, Base
from app.models.all_models import User, Lead, ChatLog, RequestQueue, ProcessingLog
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    logger.info("Creating tables in database...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully!")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")

if __name__ == "__main__":
    init_db()
