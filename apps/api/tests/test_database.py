import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.infrastructure.database import get_engine, get_session_factory
from app.main import app

@pytest.mark.integration
def test_real_postgres_and_request_sessions():
    assert get_engine().dialect.name == "postgresql"
    factory = get_session_factory()
    with factory() as first, factory() as second:
        assert first is not second
        assert first.execute(text("SELECT 1")).scalar_one() == 1
        assert "PostgreSQL" in second.execute(text("SELECT version()")).scalar_one()
    with TestClient(app) as client:
        response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "database"}
