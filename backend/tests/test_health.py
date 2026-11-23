"""Tests for /api/health. Run with: docker compose run --rm api pytest -q"""

from fastapi.testclient import TestClient

from app.main import app

# TestClient calls the app directly, without starting a real server or using the network.
client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_mode():
    # The mode must be one of the two allowed values.
    assert client.get("/api/health").json()["mode"] in ("mock", "real")


def test_health_finds_ffmpeg():
    # Passes inside Docker because the Dockerfile installs ffmpeg.
    assert client.get("/api/health").json()["ffmpeg"] is True
