import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from langchain_core.messages import AIMessage
from src.main import app
from src.agent.schema import RouterIntent

client = TestClient(app)

@pytest.mark.priority("P0")
def test_chat_e2e_successful_turn():
    """
    Priority: P0
    Description: Performance End-to-End validation of the /chat/ endpoint.
    Responsibility: Verifies API -> Graph -> Response lifecycle.
    """
    # Mocking the graph execution to prevent expensive LLM calls during E2E API tests
    # We want to test the FastAPI glue code and response formatting.
    
    mock_result = {
        "messages": [
            AIMessage(content="您好！我是 GeoTrave 助手，请问有什么可以帮您？")
        ],
        "latest_intent": "chit_chat_or_malicious"
    }

    with patch("src.api.chat.graph_app.ainvoke", new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = mock_result
        
        response = client.post(
            "/chat/",
            json={
                "message": "你好",
                "session_id": "test_e2e_session_1"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "助手" in data["reply"]
        assert data["session_id"] == "test_e2e_session_1"

@pytest.mark.priority("P1")
def test_chat_e2e_error_handling():
    """
    Priority: P1
    Description: Verifies that API returns a graceful error structure when graph fails.
    """
    with patch("src.api.chat.graph_app.ainvoke", side_effect=Exception("Graph Engine Crash")):
        response = client.post(
            "/chat/",
            json={
                "message": "故障测试",
                "session_id": "error_session"
            }
        )
        
        assert response.status_code == 200 # App handles exception gracefully
        data = response.json()
        assert data["status"] == "error"
        assert "Graph Engine Crash" in data["reply"]
