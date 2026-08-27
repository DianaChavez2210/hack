"""
Pruebas de Integración para los Endpoints FastAPI Backend (app/).
HealthSignal LATAM — RISA Data V1.0.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["system"] == "HealthSignal LATAM"


def test_get_patients_endpoint():
    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "patients" in data


def test_get_signals_endpoint():
    response = client.get("/api/v1/signals")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "signals" in data


def test_get_technical_alerts_endpoint():
    response = client.get("/api/v1/alerts/technical")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "alerts" in data


if __name__ == "__main__":
    pytest.main([__file__])
