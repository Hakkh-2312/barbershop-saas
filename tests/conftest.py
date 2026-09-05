import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - registers all models on Base.metadata
from app.core.limiter import limiter
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# The test suite signs up/logs in far more than the production rate limits
# allow (e.g. once per test via the auth_headers fixture below) - rate
# limiting itself is exercised in test_rate_limiting.py with the limiter
# re-enabled just for that test.
limiter.enabled = False

# Defaults to a local Postgres (e.g. the "db" service in docker-compose.yml).
# Postgres is required, not optional: the overlap-prevention exclusion
# constraint on `appointments` uses gist/btree_gist and tsrange, which have
# no SQLite equivalent.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres",
)

# All test tables live in their own schema so this suite can never touch
# whatever else lives in the target database (e.g. a shared dev DB).
TEST_SCHEMA = "test"


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL).execution_options(
        schema_translate_map={None: TEST_SCHEMA}
    )

    with create_engine(TEST_DATABASE_URL).connect() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE'))
        conn.execute(text(f'CREATE SCHEMA "{TEST_SCHEMA}"'))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        conn.commit()

    Base.metadata.create_all(eng)

    yield eng

    eng.dispose()
    with create_engine(TEST_DATABASE_URL).connect() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{TEST_SCHEMA}" CASCADE'))
        conn.commit()


@pytest.fixture()
def db_session(engine):
    """A session bound to a connection-level transaction that's always
    rolled back, so each test starts clean even though route handlers call
    db.commit() themselves (see SQLAlchemy's "joining a session into an
    external transaction" pattern)."""
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """Signs up a fresh tenant and returns (headers, tenant_name) for tests
    that need an authenticated user but don't care about the specifics."""

    def _make(email="owner@example.com", tenant_name="Test Shop", password="supersecret123"):
        resp = client.post(
            "/api/auth/signup",
            json={"tenant_name": tenant_name, "email": email, "password": password},
        )
        assert resp.status_code == 201, resp.text
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make


@pytest.fixture()
def shop(client, auth_headers):
    """A fully set-up tenant: open 09:00-18:00 every day, one customer, one
    20-minute service. Returns (headers, customer_id, service_id)."""
    headers = auth_headers(email="shop@example.com", tenant_name="Fully Set Up Shop")

    for day in range(7):
        resp = client.put(
            f"/api/working-hours/{day}",
            headers=headers,
            json={"start_time": "09:00:00", "end_time": "18:00:00", "is_closed": False},
        )
        assert resp.status_code == 200, resp.text

    customer = client.post(
        "/api/customers",
        headers=headers,
        json={"name": "Regular Customer", "phone": "0501234567"},
    ).json()

    service = client.post(
        "/api/services",
        headers=headers,
        json={"name": "Haircut", "duration_minutes": 20, "price": 50},
    ).json()

    return headers, customer["id"], service["id"]
