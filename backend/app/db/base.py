from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import logging
from app.core.config import settings

logger = logging.getLogger("tat_guardian.db")

# Setup engine with fallback capability for development flexibility
database_url = settings.DATABASE_URL
engine_kwargs = {}

if "sqlite" in database_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(database_url, **engine_kwargs)
else:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20
    })
    try:
        test_engine = create_engine(database_url, **engine_kwargs)
        with test_engine.connect() as conn:
            pass
        engine = test_engine
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL ({e}). Falling back to SQLite for local standalone development...")
        fallback_url = settings.SQLITE_FALLBACK_URL
        engine = create_engine(fallback_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
