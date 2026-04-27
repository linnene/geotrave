"""
Description: API Schema and Payload Validation Test Suite
Mapping: /src/api/schema.py
Priority: P1 - Interface Integrity
Main Test Items:
1. ChatRequest input validation (P1)
"""

import pytest
from pydantic import ValidationError
from src.api.schema import ChatRequest


@pytest.mark.priority("P1")
def test_chat_request_validation():
    """
    Priority: P1
    Description: Verifies that ChatRequest correctly validates input fields.
    Assertion Standard:
    1. Valid data passes.
    2. Empty message raises ValidationError.
    """
    valid_req = ChatRequest(message="Hello", session_id="test_sid")
    assert valid_req.message == "Hello"
    assert valid_req.session_id == "test_sid"

    with pytest.raises(ValidationError) as exc_info:
        ChatRequest(message="")
    assert "message" in str(exc_info.value)
