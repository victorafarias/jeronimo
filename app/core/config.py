import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    DATABASE_URL: str
    
    EVOLUTION_API_URL: str
    EVOLUTION_API_KEY: str
    EVOLUTION_INSTANCE_NAME: str
    EVOLUTION_DESTINATION_URL: str
    
    N8N_WEBHOOK_URL: str
    
    LOG_LEVEL: str = "INFO"
    
    # Configurações do Dashboard e Email
    DASHBOARD_USER: str = "admin"
    DASHBOARD_PASSWORD: str = "password"
    
    EMAIL_DESTINATION: str
    EMAIL_SMTP_SERVER: str
    EMAIL_SMTP_PORT: int
    EMAIL_SMTP_USER: str
    EMAIL_SMTP_PASSWORD: str

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True
        extra = "ignore"
settings = Settings()
