"""
Description: API Schema and Payload Validation Test Suite
Mapping: /src/api/schema.py
Priority: P1 - Interface Integrity
Main Test Items:
1. ChatRequest input validation (P1)
2. RAG InsertRequest content constraints (P1)
3. SearchRequest k-value boundary conditions (P2)
"""

import pytest
from pydantic import ValidationError
from src.api.schema import ChatRequest, SearchRequest, DocumentItem, InsertRequest

@pytest.mark.priority("P1")
def test_chat_request_validation():
    """
    Priority: P1
    Description: Verifies that ChatRequest correctly validates input fields.
    Assertion Standard: 
    1. Valid data passes.
    2. Empty message raises ValidationError.
    """
    # 1. Valid data
    valid_req = ChatRequest(message="Hello", session_id="test_sid")
    assert valid_req.message == "Hello"
    assert valid_req.session_id == "test_sid"

    # 2. Empty message
    with pytest.raises(ValidationError) as exc_info:
        ChatRequest(message="")
    assert "message" in str(exc_info.value), "Validation Error: Should reject empty messages."

@pytest.mark.priority("P2")
def test_search_request_k_boundaries():
    """
    Priority: P2
    Description: Verifies k-value limits (ge=1, le=10).
    Assertion Standard: 
    1. k=1 and k=10 pass.
    2. k=0 or k=11 raises ValidationError.
    """
    # 1. Valid boundaries
    assert SearchRequest(query="test", k=1).k == 1
    assert SearchRequest(query="test", k=10).k == 10

    # 2. Invalid low boundary (ge=1)
    with pytest.raises(ValidationError):
        SearchRequest(query="test", k=0)

    # 3. Invalid high boundary (le=10)
    with pytest.raises(ValidationError):
        SearchRequest(query="test", k=11)

@pytest.mark.priority("P1")
def test_insert_request_structure():
    """
    Priority: P1
    Description: Verifies structure of bulk insertion requests.
    Assertion Standard: Ensures documents list is processed correctly.
    """
    item = DocumentItem(content="Some knowledge", metadata={"source": "test"})
    req = InsertRequest(documents=[item])
    assert len(req.documents) == 1
    assert req.documents[0].content == "Some knowledge"

