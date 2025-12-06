from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Usar psycopg2 para síncrono (FastAPI/Workers padrão) e asyncpg se necessário futuramente
# Por enquanto vamos de síncrono para simplicidade do iniciante, 
# mas os workers rodarão em threads/processos separados.

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
