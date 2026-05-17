"""
Test Suite: Session Store
Mapping: /src/database/session_store.py
Priority: P0 — Session metadata persistence
"""

import pytest

from src.database.session_store import SqliteSessionStore


async def _new_store():
    s = await SqliteSessionStore.get_instance(":memory:")
    SqliteSessionStore._instances.clear()
    return s


# =============================================================================
# P0 — CRUD
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_create_and_get():
    store = await _new_store()
    s = await store.create("sid1", title="Test", last_message="Hello")
    assert s.session_id == "sid1"
    assert s.title == "Test"
    assert s.last_message == "Hello"
    assert s.created_at
    assert s.updated_at

    retrieved = await store.get("sid1")
    assert retrieved is not None
    assert retrieved.title == "Test"
    assert retrieved.last_message == "Hello"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_get_missing():
    store = await _new_store()
    assert await store.get("nonexistent") is None


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_list_all_ordered():
    store = await _new_store()
    await store.create("s1", title="First")
    await store.create("s2", title="Second")
    await store.create("s3", title="Third")

    sessions = await store.list_all()
    assert len(sessions) == 3
    ids = {s.session_id for s in sessions}
    assert ids == {"s1", "s2", "s3"}


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_update():
    store = await _new_store()
    await store.create("sid1", title="Original")

    updated = await store.update("sid1", title="Changed", last_message="msg")
    assert updated is not None
    assert updated.title == "Changed"
    assert updated.last_message == "msg"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_update_missing():
    store = await _new_store()
    assert await store.update("nonexistent", title="X") is None


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_delete():
    store = await _new_store()
    await store.create("sid1", title="ToDelete")
    assert await store.get("sid1") is not None

    result = await store.delete("sid1")
    assert result is True
    assert await store.get("sid1") is None


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_delete_missing():
    store = await _new_store()
    assert await store.delete("nonexistent") is False


# =============================================================================
# P1 — Upsert
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_upsert_new_session():
    store = await _new_store()
    s = await store.upsert_on_success("new_sid", "Hello world")
    assert s.session_id == "new_sid"
    assert s.last_message == "Hello world"
    assert s.title == "Hello world"[:50]


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_upsert_existing_session():
    store = await _new_store()
    await store.create("sid1", title="Old Title", last_message="Old msg")

    s = await store.upsert_on_success("sid1", "New msg")
    assert s.session_id == "sid1"
    assert s.last_message == "New msg"
    assert s.title == "Old Title"
