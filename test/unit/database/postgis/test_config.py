"""
Test Suite: PostGIS Config
Mapping: /src/database/postgis/config.py
Priority: P1 - Configuration Integrity
"""

import os
import pytest


@pytest.mark.priority("P0")
def test_default_dsn():
    """
    Priority: P0
    Description: Default POSTGIS_DSN fallback when env variable is not set.
    """
    os.environ.pop("POSTGIS_DSN", None)
    from src.database.postgis.config import POSTGIS_DSN

    assert "geotrave" in POSTGIS_DSN, (
        f"默认 DSN 应包含默认用户名 'geotrave'，实际值: {POSTGIS_DSN}"
    )
    assert "localhost" in POSTGIS_DSN, (
        f"默认 DSN 应指向 localhost，实际值: {POSTGIS_DSN}"
    )
    assert "5432" in POSTGIS_DSN, (
        f"默认 DSN 应使用端口 5432，实际值: {POSTGIS_DSN}"
    )


@pytest.mark.priority("P1")
def test_custom_dsn_from_env(monkeypatch):
    """
    Priority: P1
    Description: POSTGIS_DSN reads from environment variable when set.
    """
    custom_dsn = "postgresql://testuser:testpass@testhost:9999/testdb"
    monkeypatch.setenv("POSTGIS_DSN", custom_dsn)

    import importlib
    from src.database.postgis import config
    importlib.reload(config)

    assert config.POSTGIS_DSN == custom_dsn, (
        f"DSN 应从环境变量读取，预期: {custom_dsn}，实际: {config.POSTGIS_DSN}"
    )
