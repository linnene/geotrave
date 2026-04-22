"""
Description: Infrastructure and Utility Test Suite
Mapping: /src/utils/
Priority: P0 - Critical Foundation
Main Test Items:
1. LLMFactory singleton and instance management (P0)
2. Config loading and environment integrity (P1)
3. Prompt template formatting and safety (P1)
"""

import pytest
from agent.llm_factory import LLMFactory
from src.utils import config

@pytest.mark.priority("P0")
def test_llm_factory_singleton():
    """
    Priority: P0
    Description: Verifies that LLMFactory maintains a single instance per config key.
    Responsibility: Prevents memory leaks and redundant API connections.
    Assertion Standard: Multiple requests for the same model must return the identical object ID.
    """
    # Using 'router' as it is a valid node type in LLMFactory
    node_type = "router"
    instance1 = LLMFactory.get_model(node_type)
    instance2 = LLMFactory.get_model(node_type)
    
    # Assert identity
    assert instance1 is instance2, (
        f"Singleton Violation: Factory returned different instances for node type '{node_type}'. "
        f"Instance1 ID: {id(instance1)}, Instance2 ID: {id(instance2)}"
    )

@pytest.mark.priority("P1")
def test_llm_factory_different_models():
    """
    Priority: P1
    Description: Verifies that different model IDs return distinct instances.
    """
    m1 = LLMFactory.get_model("router")
    m2 = LLMFactory.get_model("analyzer")
    
    assert m1 is not m2, "Logic Error: Factory returned identical instance for different node types."

@pytest.mark.priority("P1")
def test_config_environment_loading():
    """
    Priority: P1
    Description: Validates that critical system variables are loaded correctly.
    Responsibility: Prevents runtime crashes due to missing keys.
    Assertion Standard: Config object must contain core fields.
    """
    # Environment variables should be present in the config object
    critical_fields = ["CHROMA_DB_DIR", "EMBEDDING_MODEL"]
    for field in critical_fields:
        val = getattr(config, field, None)
        assert val is not None, f"Config Critical Failure: Field '{field}' is missing or None."
        assert str(val).strip() != "", f"Config Critical Failure: Field '{field}' is an empty string."


