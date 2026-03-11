from fastapi.testclient import TestClient
from app.main import app

def test_health_check():
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Service is running"
        assert data["http_api_enabled"] is True
    
