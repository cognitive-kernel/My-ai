from fastapi.testclient import TestClient
from my_ai.api import app
def test_health():
    with TestClient(app) as client:
        r=client.get("/health"); assert r.status_code==200; assert r.json()["status"]=="ok"
def test_home():
    with TestClient(app) as client: assert client.get("/").status_code==200
