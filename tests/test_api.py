"""Tests voor de RAG API endpoints."""

from fastapi.testclient import TestClient
from unittest.mock import patch

from src.api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "Obsidian Cloud Brain"


def test_ask_endpoint_success():
    mock_result = {
        "answer": "Azure is een cloud platform.",
        "sources": [{"title": "Azure Intro", "path": "azure/intro.md"}],
    }
    with patch("src.api.main.ask", return_value=mock_result):
        response = client.post("/ask", json={"question": "Wat is Azure?"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Azure is een cloud platform."
    assert len(data["sources"]) == 1


def test_ask_endpoint_validation_error():
    # Question too short (< 3 characters)
    response = client.post("/ask", json={"question": "hi"})
    assert response.status_code == 422


def test_ask_endpoint_server_error():
    with patch("src.api.main.ask", side_effect=Exception("Azure is down")):
        response = client.post("/ask", json={"question": "Wat is mijn planning?"})
    assert response.status_code == 500
