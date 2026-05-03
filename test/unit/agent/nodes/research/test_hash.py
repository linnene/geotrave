"""
Test Suite: Hash Node
Mapping: /src/agent/nodes/research/hash.py
Priority: P0 - Research Loop persistence gate
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.agent.state.schema import (
    CriticResult,
    ExecutionSigns,
    ResearchLoopInternal,
    ResearchManifest,
)


# =============================================================================
# P0 — generate_hash_key
# =============================================================================


@pytest.mark.priority("P0")
def test_generate_hash_key_deterministic():
    """相同输入 → 相同 hash。"""
    from src.agent.nodes.research.hash.node import generate_hash_key

    h1 = generate_hash_key("test query", {"a": 1, "b": 2})
    h2 = generate_hash_key("test query", {"a": 1, "b": 2})

    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex digest
    assert isinstance(h1, str)


@pytest.mark.priority("P0")
def test_generate_hash_key_different_content():
    """不同 content → 不同 hash。"""
    from src.agent.nodes.research.hash.node import generate_hash_key

    h1 = generate_hash_key("query", {"x": 1})
    h2 = generate_hash_key("query", {"x": 2})

    assert h1 != h2


@pytest.mark.priority("P1")
def test_generate_hash_key_different_query():
    """不同 query → 不同 hash。"""
    from src.agent.nodes.research.hash.node import generate_hash_key

    h1 = generate_hash_key("q1", {"a": 1})
    h2 = generate_hash_key("q2", {"a": 1})

    assert h1 != h2


# =============================================================================
# P0 — persist_results
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_persist_results_creates_mapping():
    """验证 hash_key 生成和 query→hashes 映射正确。"""
    from src.agent.nodes.research.hash.node import persist_results

    results = [
        CriticResult(
            query="东京酒店",
            safety_tag="safe",
            relevance_score=90.0,
            utility_score=85.0,
            rationale="精确匹配",
        ),
        CriticResult(
            query="东京酒店",
            safety_tag="safe",
            relevance_score=75.0,
            utility_score=70.0,
            rationale="另一家酒店",
        ),
        CriticResult(
            query="大阪美食",
            safety_tag="safe",
            relevance_score=88.0,
            utility_score=80.0,
            rationale="道顿堀拉面",
        ),
    ]

    with patch(
        "src.agent.nodes.research.hash.node.batch_store_results",
        new=AsyncMock(),
    ) as mock_store:
        mapping = await persist_results(results, {}, "sess-test")

    # 验证 batch_store_results 被调用
    mock_store.assert_awaited_once()

    # 验证映射结构: {query: [hash_key, ...]}
    assert "东京酒店" in mapping
    assert "大阪美食" in mapping
    assert len(mapping["东京酒店"]) == 2
    assert len(mapping["大阪美食"]) == 1

    # 同一 query 的两条结果应有不同 hash
    assert mapping["东京酒店"][0] != mapping["东京酒店"][1]

    # 验证存入的 records 包含 hash_key 和 payload
    call_args = mock_store.call_args
    records = call_args[0][0]
    passed_session = call_args[0][1]
    assert passed_session == "sess-test"
    assert len(records) == 3
    for record in records:
        assert "hash_key" in record
        assert "payload" in record
        assert isinstance(record["hash_key"], str)
        assert len(record["hash_key"]) == 64


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_persist_results_empty_list():
    """空列表 → 不调用 batch_store，返回空 dict。"""
    from src.agent.nodes.research.hash.node import persist_results

    with patch(
        "src.agent.nodes.research.hash.node.batch_store_results",
        new=AsyncMock(),
    ) as mock_store:
        mapping = await persist_results([], {}, "sess")

    mock_store.assert_not_called()
    assert mapping == {}


# =============================================================================
# P0 — hash_node
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_hash_node_empty_skips():
    """无通过结果 → 跳过持久化，设置 is_loop_exit。"""
    from src.agent.nodes.research.hash.node import hash_node

    loop_state = ResearchLoopInternal(all_passed_results=[])
    manifest = ResearchManifest(loop_state=loop_state)
    state = {"research_data": manifest, "messages": []}

    result = await hash_node(state)

    signs = result.get("execution_signs")
    assert signs is not None
    assert signs.is_loop_exit is True

    traces = result.get("trace_history", [])
    assert traces[0].status == "SKIPPED"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_hash_node_persists_and_exposes_hashes():
    """验证持久化 + research_hashes 写入 + is_loop_exit 设置。"""
    from src.agent.nodes.research.hash.node import hash_node

    passed = [
        CriticResult(
            query="东京酒店",
            safety_tag="safe",
            relevance_score=90.0,
            utility_score=85.0,
            rationale="好",
        ),
        CriticResult(
            query="大阪美食",
            safety_tag="safe",
            relevance_score=88.0,
            utility_score=80.0,
            rationale="好",
        ),
    ]
    loop_state = ResearchLoopInternal(all_passed_results=passed)
    manifest = ResearchManifest(loop_state=loop_state)
    state = {
        "research_data": manifest,
        "messages": [],
    }

    with patch(
        "src.agent.nodes.research.hash.node.batch_store_results",
        new=AsyncMock(),
    ) as mock_store:
        result = await hash_node(state)

    # batch_store 被调用
    mock_store.assert_awaited_once()

    # research_hashes 已填充
    new_manifest = result["research_data"]
    hashes = new_manifest.research_hashes
    assert "东京酒店" in hashes
    assert "大阪美食" in hashes
    assert len(hashes["东京酒店"]) == 1
    assert len(hashes["大阪美食"]) == 1

    # is_loop_exit 已设置
    signs = result["execution_signs"]
    assert signs.is_loop_exit is True

    # trace 正确
    traces = result["trace_history"]
    assert traces[0].status == "SUCCESS"
    assert traces[0].detail["persisted_count"] == 2
    assert traces[0].detail["hash_groups"] == 2


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_hash_node_merges_existing_hashes():
    """已有 research_hashes 时，新 hash 正确合并而非覆盖。"""
    from src.agent.nodes.research.hash.node import hash_node

    passed = [
        CriticResult(
            query="东京酒店",
            safety_tag="safe",
            relevance_score=75.0,
            utility_score=70.0,
            rationale="补充结果",
        ),
    ]
    loop_state = ResearchLoopInternal(all_passed_results=passed)
    existing_hashes = {"东京酒店": ["existing_hash_abc"], "京都景点": ["old_hash_xyz"]}
    manifest = ResearchManifest(
        loop_state=loop_state,
        research_hashes=existing_hashes,
    )
    state = {"research_data": manifest, "messages": []}

    with patch(
        "src.agent.nodes.research.hash.node.batch_store_results",
        new=AsyncMock(),
    ):
        result = await hash_node(state)

    hashes = result["research_data"].research_hashes
    # 旧 query 保留原有 hash + 新增
    assert len(hashes["东京酒店"]) == 2
    assert "existing_hash_abc" in hashes["东京酒店"]
    # 无关 query 不受影响
    assert "京都景点" in hashes
    assert hashes["京都景点"] == ["old_hash_xyz"]


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_hash_node_dedup_same_query_same_content():
    """同一 query 的同一内容产生相同 hash → 合并时去重。"""
    from src.agent.nodes.research.hash.node import hash_node, generate_hash_key

    # 构造两条完全相同的 CriticResult
    r = CriticResult(
        query="札幌温泉",
        safety_tag="safe",
        relevance_score=95.0,
        utility_score=90.0,
        rationale="登别温泉推荐",
    )
    # 生成它们的 hash
    hk = generate_hash_key(r.query, r.model_dump())

    # 第二轮: 同样的结果再次通过 Critic
    passed = [r]
    existing_hashes = {"札幌温泉": [hk]}
    loop_state = ResearchLoopInternal(all_passed_results=passed)
    manifest = ResearchManifest(
        loop_state=loop_state,
        research_hashes=existing_hashes,
    )
    state = {"research_data": manifest, "messages": []}

    with patch(
        "src.agent.nodes.research.hash.node.batch_store_results",
        new=AsyncMock(),
    ):
        result = await hash_node(state)

    # 重复 hash 不应重复添加
    hashes = result["research_data"].research_hashes
    assert hashes["札幌温泉"] == [hk]


# =============================================================================
# P0 — matched_doc_ids 合并
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_hash_node_promotes_passed_doc_ids():
    """passed_doc_ids → matched_doc_ids 提升。"""
    from src.agent.nodes.research.hash.node import hash_node

    passed = [
        CriticResult(
            query="东京酒店",
            safety_tag="safe",
            relevance_score=90.0,
            utility_score=85.0,
            rationale="好",
        ),
    ]
    loop_state = ResearchLoopInternal(
        all_passed_results=passed,
        passed_doc_ids=["doc_abc", "doc_def"],
    )
    manifest = ResearchManifest(loop_state=loop_state)
    state = {"research_data": manifest, "messages": []}

    with patch(
        "src.agent.nodes.research.hash.node.batch_store_results",
        new=AsyncMock(),
    ):
        result = await hash_node(state)

    new_manifest = result["research_data"]
    assert "doc_abc" in new_manifest.matched_doc_ids
    assert "doc_def" in new_manifest.matched_doc_ids
    assert len(new_manifest.matched_doc_ids) == 2


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_hash_node_merges_matched_doc_ids():
    """已有 matched_doc_ids 时，新 doc_id 追加而非覆盖。"""
    from src.agent.nodes.research.hash.node import hash_node

    loop_state = ResearchLoopInternal(
        all_passed_results=[],
        passed_doc_ids=["doc_new"],
    )
    manifest = ResearchManifest(
        loop_state=loop_state,
        matched_doc_ids=["doc_existing"],
    )
    state = {"research_data": manifest, "messages": []}

    result = await hash_node(state)

    new_manifest = result["research_data"]
    assert len(new_manifest.matched_doc_ids) == 2
    assert "doc_existing" in new_manifest.matched_doc_ids
    assert "doc_new" in new_manifest.matched_doc_ids


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_hash_node_dedup_matched_doc_ids():
    """重复 doc_id 不会重复写入 matched_doc_ids。"""
    from src.agent.nodes.research.hash.node import hash_node

    loop_state = ResearchLoopInternal(
        all_passed_results=[],
        passed_doc_ids=["doc_a", "doc_b"],
    )
    manifest = ResearchManifest(
        loop_state=loop_state,
        matched_doc_ids=["doc_a"],  # 已有
    )
    state = {"research_data": manifest, "messages": []}

    result = await hash_node(state)

    new_manifest = result["research_data"]
    assert len(new_manifest.matched_doc_ids) == 2
    assert "doc_a" in new_manifest.matched_doc_ids
    assert "doc_b" in new_manifest.matched_doc_ids


# =============================================================================
# P0 — web_search 拆分结果多 hash key
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_persist_results_split_web_search():
    """拆分后的 web_search 结果（key 含 #0/#1）各自独立 hash 并存入同一查询组。"""
    from src.agent.nodes.research.hash.node import persist_results

    query_params = '{"query": "京都红叶", "max_results": 3}'
    results = [
        CriticResult(
            query=f"{query_params}#0",
            tool_name="web_search",
            safety_tag="safe",
            relevance_score=90.0,
            utility_score=85.0,
            rationale="永观堂",
        ),
        CriticResult(
            query=f"{query_params}#1",
            tool_name="web_search",
            safety_tag="safe",
            relevance_score=75.0,
            utility_score=70.0,
            rationale="清水寺",
        ),
    ]

    # query_results 使用拆分后的 key
    query_results = {
        f"{query_params}#0": {
            "content": {"title": "永观堂", "url": "https://a.com/1", "snippet": "s1", "content": "美景"},
        },
        f"{query_params}#1": {
            "content": {"title": "清水寺", "url": "https://a.com/2", "snippet": "s2", "content": "绝美"},
        },
    }

    with patch(
        "src.agent.nodes.research.hash.node.batch_store_results",
        new=AsyncMock(),
    ) as mock_store:
        mapping = await persist_results(results, query_results, "sess-test")

    # 每个结果各一条 record
    mock_store.assert_awaited_once()
    records = mock_store.call_args[0][0]
    assert len(records) == 2

    # 各自独立 hash
    assert mapping[f"{query_params}#0"][0] != mapping[f"{query_params}#1"][0]

    # 每条 record 的 payload 包含 _research_content（单个结果）
    for record in records:
        assert "_research_content" in record["payload"]
        rc = record["payload"]["_research_content"]
        assert "url" in rc
        assert "title" in rc


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_persist_results_split_key_lookup_safety():
    """拆分 key 在 query_results 中不存在时不会崩溃（raw=None 路径）。"""
    from src.agent.nodes.research.hash.node import persist_results

    query_params = '{"query": "测试", "max_results": 1}'
    results = [
        CriticResult(
            query=f"{query_params}#0",
            tool_name="web_search",
            safety_tag="safe",
            relevance_score=80.0,
            utility_score=75.0,
            rationale="测试",
        ),
    ]

    with patch(
        "src.agent.nodes.research.hash.node.batch_store_results",
        new=AsyncMock(),
    ):
        mapping = await persist_results(results, {}, "sess")

    # raw=None 时仍生成 hash 和 record，不崩溃
    assert len(mapping) == 1
    assert mapping[f"{query_params}#0"][0] != ""


