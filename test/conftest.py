"""
Description: Test Configuration & Fixtures Initialization
Mapping: Global test setup
Priority: P0 - Prerequisite for all test execution
Main Test Items:
1. SysPath Management (P0)
2. Global Asyncio Loop Scoping (P0)
"""

import os
import sys
import pytest

# Ensure src directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

@pytest.fixture(scope="session")
def anyio_backend():
    """
    Priority: P0
    Description: Configures the backend for async tests.
    Responsibility: Ensures consistency across different async environments.
    """
    return "asyncio"

