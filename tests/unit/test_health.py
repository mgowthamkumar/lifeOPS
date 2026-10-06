import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "LifeOps AI"
    assert data["status"] == "online"
    assert data["health_url"] == "/api/health"

def test_health_endpoint(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "timestamp" in data
    assert data["app_name"] == "LifeOps AI"
    assert data["database"]["connected"] is True
    assert data["database"]["type"] in ["sqlite", "postgresql"]
    assert "vector_db" in data
    assert "llm" in data
