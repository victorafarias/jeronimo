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
    Usa try/except para evitar erros se a coluna já existir.
    """
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        # Alterado: Usando try/except em vez de verificar information_schema
        # Isso é mais confiável para detectar se a coluna já existe
        
        # Tenta adicionar coluna email
        try:
            print("Adicionando coluna 'email' na tabela 'users'...")
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR NULL"))
            conn.commit()
            print("✅ Coluna 'email' adicionada com sucesso!")
        except Exception as e:
            if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                print("⚠️ Coluna 'email' já existe, pulando...")
            else:
                print(f"❌ Erro ao adicionar 'email': {e}")
        
        # Tenta adicionar coluna is_canceled
        try:
            print("Adicionando coluna 'is_canceled' na tabela 'users'...")
            conn.execute(text("ALTER TABLE users ADD COLUMN is_canceled BOOLEAN DEFAULT FALSE"))
            conn.commit()
            print("✅ Coluna 'is_canceled' adicionada com sucesso!")
        except Exception as e:
            if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                print("⚠️ Coluna 'is_canceled' já existe, pulando...")
            else:
                print(f"❌ Erro ao adicionar 'is_canceled': {e}")
        
        print("\n🎉 Migração concluída!")

if __name__ == "__main__":
    run_migration()

