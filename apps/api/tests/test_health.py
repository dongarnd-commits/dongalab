from fastapi.testclient import TestClient
from app.main import app

def test_application_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "api"}

def test_openapi_contract():
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
    assert {"/health", "/health/db"} <= schema["paths"].keys()
    assert "503" in schema["paths"]["/health/db"]["get"]["responses"]

def test_cors_origin_boundary():
    with TestClient(app) as client:
        allowed = client.get("/health", headers={"Origin": "http://localhost:3000"})
        denied = client.get("/health", headers={"Origin": "http://untrusted.example"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "access-control-allow-origin" not in denied.headers
