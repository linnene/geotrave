"""
Test Suite: Session API
Mapping: /src/api/session.py
Priority: P0 — Session CRUD endpoints
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.api.schema import CreateSessionRequest, UpdateSessionRequest


async def _mock_store(return_sessions=None, return_session=None):
    """Create a mock SqliteSessionStore."""
    mock = AsyncMock()
    mock.list_all = AsyncMock(return_value=return_sessions or [])
    mock.create = AsyncMock(return_value=return_session)
    mock.update = AsyncMock(return_value=return_session)
    mock.delete = AsyncMock(return_value=True)
    mock.get_instance = AsyncMock(return_value=mock)
    return mock


# =============================================================================
# P0 — List
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_list_sessions():
    from src.database.session_store import SessionMetadata
    from src.api.session import list_sessions

    s1 = SessionMetadata(session_id="s1", title="Test 1")
    s2 = SessionMetadata(session_id="s2", title="Test 2")
    store = await _mock_store(return_sessions=[s2, s1])

    with patch("src.api.session.SqliteSessionStore.get_instance", store.get_instance):
        result = await list_sessions()

    assert result["count"] == 2
    assert result["sessions"][0].session_id == "s2"


# =============================================================================
# P0 — Create
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_create_session():
    from src.database.session_store import SessionMetadata
    from src.api.session import create_session

    expected = SessionMetadata(session_id="new_sid", title="新对话")
    store = await _mock_store(return_session=expected)

    with patch("src.api.session.SqliteSessionStore.get_instance", store.get_instance):
        result = await create_session(CreateSessionRequest(session_id="new_sid"))

    assert result.session_id == "new_sid"
    store.create.assert_awaited_once_with(session_id="new_sid", title="新对话")


# =============================================================================
# P0 — Update
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_update_session():
    from src.database.session_store import SessionMetadata
    from src.api.session import update_session

    updated = SessionMetadata(session_id="sid", title="Changed", last_message="msg")
    store = await _mock_store(return_session=updated)

    with patch("src.api.session.SqliteSessionStore.get_instance", store.get_instance):
        result = await update_session(
            "sid",
            UpdateSessionRequest(title="Changed", last_message="msg"),
        )

    assert result.title == "Changed"
    assert result.last_message == "msg"


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_update_session_not_found():
    from src.api.session import update_session
    from fastapi import HTTPException

    store = await _mock_store(return_session=None)

    with patch("src.api.session.SqliteSessionStore.get_instance", store.get_instance):
        with pytest.raises(HTTPException) as exc:
            await update_session("missing", UpdateSessionRequest(title="X"))
        assert exc.value.status_code == 404


# =============================================================================
# P0 — Delete
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_delete_session():
    from src.api.session import delete_session

    store = await _mock_store()

    with patch("src.api.session.SqliteSessionStore.get_instance", store.get_instance):
        result = await delete_session("sid")

    assert result["status"] == "deleted"
    assert result["session_id"] == "sid"
    store.delete.assert_awaited_once_with("sid")


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_delete_session_not_found():
    from src.api.session import delete_session
    from fastapi import HTTPException

    store = await _mock_store()
    store.delete = AsyncMock(return_value=False)

    with patch("src.api.session.SqliteSessionStore.get_instance", store.get_instance):
        with pytest.raises(HTTPException) as exc:
            await delete_session("missing")
        assert exc.value.status_code == 404