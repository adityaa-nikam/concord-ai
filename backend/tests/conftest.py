import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import app.db.base as db_base
from app.db.base import Base, get_db
from app.db.seed import seed_database
from app.services.action_gateway import ActionGateway
from app.main import app

# StaticPool shared in-memory SQLite connection for isolated test runs
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override engine in db_base so lifespan and SessionLocal use test engine
db_base.engine = engine
db_base.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="function", autouse=True)
def setup_test_db():
    ActionGateway.clear_registry()
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    seed_database(session)
    session.close()
    yield
    Base.metadata.drop_all(bind=engine)
    ActionGateway.clear_registry()


@pytest.fixture
def db_session(setup_test_db):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(setup_test_db):
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
