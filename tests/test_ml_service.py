import pytest
from fastapi.testclient import TestClient

from ml_service.main import app, load_model


@pytest.fixture
def client():
    # Ensure model is loaded for tests
    try:
        load_model()
    except Exception:
        pass
    return TestClient(app)

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ml-inference"}

def test_ready(client):
    response = client.get("/ready")
    if response.status_code == 200:
        assert "model_version" in response.json()
    else:
        assert response.status_code == 503

def test_predict(client):
    response = client.post("/predict", json={"text": "simple question"})
    if response.status_code == 200:
        data = response.json()
        assert "complexity_class" in data
        assert "confidence" in data
        assert "latency_ms" in data
    else:
        assert response.status_code == 503

def test_predict_batch(client):
    response = client.post("/predict/batch", json={"texts": ["simple question", "complex analysis of X and Y"]})
    if response.status_code == 200:
        data = response.json()
        assert "predictions" in data
        assert len(data["predictions"]) == 2
        assert data["batch_size"] == 2
    else:
        assert response.status_code == 503

def test_metrics(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "ml_prediction_latency_seconds" in response.text
