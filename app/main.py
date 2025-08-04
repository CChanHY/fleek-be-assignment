from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import init_db, close_db
from app.core.logging import setup_logging
from app.api.routes import router
import logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application")
    await init_db()
    yield
    logger.info("Shutting down application")
    await close_db()


app = FastAPI(
    title="Media Generation Microservice",
    description="Asynchronous media generation using Replicate API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Media Generation Microservice", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}