from fastapi import FastAPI
from .routers import api_router

app = FastAPI(title="ReStockAI", version="0.1.0")

app.include_router(api_router)
