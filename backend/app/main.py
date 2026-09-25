from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.core.logging import logger
from app.api.router import api_router
from app.db.base import Base, engine
from app.db.seed import seed_database, SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schema and checking seed data...")
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Startup DB init warning (normal in test mode): {e}")
    
    logger.info("TAT Guardian API Backend ready.")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="TAT Guardian (CONCORD AI) - Autonomous AI Teammate for Paytm UPI Dispute Resolution",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router)
