"""
API Integration Tests: Validating FastAPI endpoints for Chat and RAG.

This module uses TestClient to perform black-box testing on the API layer.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# --- Chat API Tests ---

def test_chat_endpoint_success():
    """Test successful chat interaction."""
    payload = {
        "message": "Hello, I want to go to Tokyo for 5 days.",
        "session_id": "test_session_123"
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "reply" in data
    assert data["session_id"] == "test_session_123"

def test_chat_endpoint_empty_message():
    """Test chat with empty message should fail validation."""
    payload = {
        "message": "",
        "session_id": "test_session_123"
    }
    response = client.post("/api/chat", json=payload)
    # FastAPI/Pydantic returns 422 Unprocessable Entity for validation errors
    assert response.status_code == 422


# --- RAG API Tests ---

def test_rag_stats_endpoint():
    """Test retrieving vector DB statistics."""
    response = client.get("/api/rag/stats/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "document_count" in data

def test_rag_insert_and_search():
    """Test RAG document insertion followed by a search."""
    # 1. Insert a unique document
    unique_content = "The secret ingredient of the special soup is stardust."
    insert_payload = {
        "documents": [
            {
                "content": unique_content,
                "metadata": {"category": "test"}
            }
        ]
    }
    insert_res = client.post("/api/rag/insert/", json=insert_payload)
    assert insert_res.status_code == 200
    
    # 2. Search for the unique content
    search_payload = {
        "query": "What is the secret ingredient?",
        "k": 1
    }
    search_res = client.post("/api/rag/search/", json=search_payload)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["status"] == "success"
    assert len(search_data["results"]) > 0
    assert "stardust" in search_data["results"][0]["content"].lower()

def test_rag_upload_invalid_file():
    """Test uploading a non-txt file should fail."""
    files = {'file': ('test.pdf', b'fake pdf content', 'application/pdf')}
    response = client.post("/api/rag/upload/", files=files)
    assert response.status_code == 400
    assert "only .txt files" in response.json()["detail"].lower()
