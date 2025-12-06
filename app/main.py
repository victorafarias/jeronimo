from fastapi import FastAPI
from app.api.endpoints import router as api_router
from app.core.config import settings
import logging

# Configuração de Logs
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Jeronimo Worker System")

app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Jeronimo System is running"}
