from fastapi.testclient import TestClient
from app.api.main import app
def test_health():
    assert TestClient(app).get("/health").json()["status"]=="ok"
