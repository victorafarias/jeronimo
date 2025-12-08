# Script de migração para adicionar colunas email e is_canceled na tabela users
# Execute este script uma única vez para atualizar o banco de dados

from sqlalchemy import create_engine, text
import sys
import os

# Adiciona raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.core.config import settings

def run_migration():
    """
    Adiciona as colunas 'email' e 'is_canceled' na tabela 'users'.
    """
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Verifica se a coluna email já existe
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'email'
        """))
        
        if not result.fetchone():
            print("Adicionando coluna 'email' na tabela 'users'...")
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR NULL"))
            print("✅ Coluna 'email' adicionada com sucesso!")
        else:
            print("⚠️ Coluna 'email' já existe, pulando...")
        
        # Verifica se a coluna is_canceled já existe
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'is_canceled'
        """))
        
        if not result.fetchone():
            print("Adicionando coluna 'is_canceled' na tabela 'users'...")
            conn.execute(text("ALTER TABLE users ADD COLUMN is_canceled BOOLEAN DEFAULT FALSE"))
            print("✅ Coluna 'is_canceled' adicionada com sucesso!")
        else:
            print("⚠️ Coluna 'is_canceled' já existe, pulando...")
        
        conn.commit()
        print("\n🎉 Migração concluída com sucesso!")

if __name__ == "__main__":
    run_migration()
