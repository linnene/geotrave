"""
Test Suite: Search Node
Mapping: /src/agent/nodes/search/node.py
Priority: P0 - Research Loop tool execution gate
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.agent.state import ResearchManifest, SearchTask
from src.agent.state.schema import ResearchLoopInternal, ResearchResult


# =============================================================================
# P0 — _generate_summary
# =============================================================================


@pytest.mark.priority("P0")
def test_generate_summary_poi_list():
    """POI 列表: 提取前 5 条 name。"""
    from src.agent.nodes.research.search.node import _generate_summary

    payload = {
        "pois": [
            {"name": "东京塔", "category": "景点"},
            {"name": "浅草寺", "category": "寺庙"},
            {"name": "银座", "category": "购物"},
        ]
    }
    result = _generate_summary(payload)
    assert "东京塔" in result
    assert "浅草寺" in result
    assert "银座" in result
    assert "POI:" in result


@pytest.mark.priority("P1")
def test_generate_summary_poi_truncation():
    """POI 超过 5 条: 显示前 5 + 总数。"""
    from src.agent.nodes.research.search.node import _generate_summary

    pois = [{"name": f"地点{i}"} for i in range(10)]
    result = _generate_summary({"pois": pois})
    assert "共10条" in result
    # 只有前 5 条在摘要中
    for i in range(5):
        assert f"地点{i}" in result
    assert "地点9" not in result


@pytest.mark.priority("P0")
def test_generate_summary_shortest_route():
    """最短路径: 显示起终点、距离、步行时间。"""
    from src.agent.nodes.research.search.node import _generate_summary

    payload = {
        "mode": "shortest",
        "origin": "东京站",
        "destination": "新宿站",
        "distance_km": 6.5,
        "walk_min": 85,
    }
    result = _generate_summary(payload)
    assert "东京站" in result
    assert "新宿站" in result
    assert "6.5" in result
    assert "85" in result


@pytest.mark.priority("P0")
def test_generate_summary_isochrone():
    """等时圈: 显示原点、分钟数、可达节点、最大距离。"""
    from src.agent.nodes.research.search.node import _generate_summary

    payload = {
        "mode": "isochrone",
        "origin": "札幌站",
        "isochrone_minutes": 15,
        "reachable_nodes": 42,
        "max_distance_m": 1200,
    }
    result = _generate_summary(payload)
    assert "札幌站" in result
    assert "15" in result
    assert "42" in result
    assert "1200" in result


@pytest.mark.priority("P1")
def test_generate_summary_fallback_json():
    """未知类型: fallback 为 JSON 字符串前 500 字符。"""
    from src.agent.nodes.research.search.node import _generate_summary

    payload = {"custom_field": "custom_value", "nested": {"a": 1}}
    result = _generate_summary(payload)
    assert "custom_field" in result
    assert "custom_value" in result
    assert len(result) <= 500


@pytest.mark.priority("P0")
def test_generate_summary_web_single_result():
    """单条 web_search 结果: 显示标题、摘要、内容长度、抓取状态。"""
    from src.agent.nodes.research.search.node import _generate_summary

    payload = {
        "title": "东京最值得去的10个景点",
        "url": "https://example.com/tokyo",
        "snippet": "一个详细的东京景点攻略...",
        "content": "东京塔、浅草寺、银座等经典景点...",
        "crawl_status": "success",
        "crawl_mode": "fast",
    }
    result = _generate_summary(payload)
    assert "[web]" in result
    assert "东京最值得去的10个景点" in result
    assert "东京景点攻略" in result
    assert "success" in result


@pytest.mark.priority("P1")
def test_generate_summary_web_result_no_content():
    """web 结果无全文: 仅显示标题 + snippet + 状态。"""
    from src.agent.nodes.research.search.node import _generate_summary

    payload = {
        "title": "北海道旅游指南",
        "url": "https://example.com/hokkaido",
        "snippet": "",
        "content": None,
        "crawl_status": "error",
    }
    result = _generate_summary(payload)
    assert "[web]" in result
    assert "北海道旅游指南" in result
    assert "error" in result


# =============================================================================
# P0 — _execute_tasks
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_execute_tasks_wraps_in_research_result():
    """正常执行: 每个 task 结果包裹为 ResearchResult envelope。"""
    from src.agent.nodes.research.search.node import _execute_tasks

    tasks = [
        SearchTask(
            tool_name="test_tool",
            dimension="attraction",
            parameters={"keyword": "东京塔"},
            rationale="测试用",
        )
    ]

    # mock handler 返回 RetrievalMetadata
    mock_metadata = AsyncMock()
    mock_metadata.payload = {"pois": [{"name": "东京塔", "lat": 35.6586, "lng": 139.7454}]}

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"test_tool": AsyncMock(return_value=mock_metadata)},
    ):
        results = await _execute_tasks(tasks)

    assert len(results) == 1
    query_key = next(iter(results))
    envelope = results[query_key]
    assert isinstance(envelope, ResearchResult)
    assert envelope.tool_name == "test_tool"
    assert envelope.content_type == "json"
    assert "东京塔" in envelope.content_summary
    assert envelope.content is not None


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_execute_tasks_unsupported_tool():
    """未注册工具: 创建 error envelope，不崩溃也不静默丢弃。"""
    from src.agent.nodes.research.search.node import _execute_tasks

    tasks = [
        SearchTask(
            tool_name="nonexistent_tool",
            dimension="general",
            parameters={"query": "test"},
            rationale="测试未注册工具",
        )
    ]

    with patch.dict("src.agent.nodes.research.search.tools.TOOL_DISPATCH", {}):
        results = await _execute_tasks(tasks)

    # 未注册工具创建 error envelope（不再静默丢弃）
    assert len(results) == 1
    envelope = next(iter(results.values()))
    assert isinstance(envelope, ResearchResult)
    assert "error" in envelope.content
    assert "Unknown tool" in envelope.content["error"]
    assert envelope.tool_name == "nonexistent_tool"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_execute_tasks_handler_exception():
    """handler 抛出异常: 返回 error envelope，不崩溃。"""
    from src.agent.nodes.research.search.node import _execute_tasks

    tasks = [
        SearchTask(
            tool_name="broken_tool",
            dimension="attraction",
            parameters={"keyword": "test"},
            rationale="测试异常处理",
        )
    ]

    async def broken_handler(task):
        raise RuntimeError("数据库连接超时")

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"broken_tool": broken_handler},
    ):
        results = await _execute_tasks(tasks)

    assert len(results) == 1
    envelope = next(iter(results.values()))
    assert isinstance(envelope, ResearchResult)
    assert "error" in envelope.content
    assert "执行失败" in envelope.content_summary
    assert envelope.tool_name == "broken_tool"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_execute_tasks_splits_web_search():
    """web_search 结果按 URL 拆分为多个独立 ResearchResult。"""
    from src.agent.nodes.research.search.node import _execute_tasks

    tasks = [
        SearchTask(
            tool_name="web_search",
            dimension="attraction",
            parameters={"query": "东京景点", "max_results": 3},
            rationale="测试拆分",
        )
    ]

    mock_metadata = AsyncMock()
    mock_metadata.payload = {
        "query": "东京景点",
        "total": 3,
        "results": [
            {"title": "浅草寺", "url": "https://a.com/1", "snippet": "s1", "content": "全文1", "crawl_status": "success"},
            {"title": "东京塔", "url": "https://a.com/2", "snippet": "s2", "content": "全文2", "crawl_status": "success"},
            {"title": "银座", "url": "https://a.com/3", "snippet": "s3", "content": None, "crawl_status": "error"},
        ],
    }

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"web_search": AsyncMock(return_value=mock_metadata)},
    ):
        results = await _execute_tasks(tasks)

    assert len(results) == 3
    keys = sorted(results.keys())
    assert all("#" in k for k in keys)
    assert keys[0].endswith("#0")
    assert keys[1].endswith("#1")
    assert keys[2].endswith("#2")

    # 每个 envelope 是独立的 ResearchResult
    for key in keys:
        envelope = results[key]
        assert isinstance(envelope, ResearchResult)
        assert envelope.tool_name == "web_search"
        assert envelope.content_type == "json"
        assert "url" in envelope.content  # 单个结果 dict，不是批次

    # 第三项无全文也应正常包裹
    assert results[keys[2]].content["crawl_status"] == "error"


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_execute_tasks_web_search_empty_results():
    """web_search 无结果时保留一条空 envelope。"""
    from src.agent.nodes.research.search.node import _execute_tasks

    tasks = [
        SearchTask(
            tool_name="web_search",
            dimension="attraction",
            parameters={"query": "不存在的内容xyz"},
            rationale="测试空结果",
        )
    ]

    mock_metadata = AsyncMock()
    mock_metadata.payload = {"query": "不存在的内容xyz", "total": 0, "results": []}

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"web_search": AsyncMock(return_value=mock_metadata)},
    ):
        results = await _execute_tasks(tasks)

    assert len(results) == 1
    envelope = next(iter(results.values()))
    assert isinstance(envelope, ResearchResult)
    assert "无结果" in envelope.content_summary


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_execute_tasks_non_web_search_unchanged():
    """非 web_search 工具保持一 task 一 result，不受拆分影响。"""
    from src.agent.nodes.research.search.node import _execute_tasks

    tasks = [
        SearchTask(
            tool_name="spatial_search",
            dimension="dining",
            parameters={"center": "东京", "radius_m": "1000"},
            rationale="测试",
        ),
    ]

    mock_metadata = AsyncMock()
    mock_metadata.payload = {"pois": [{"name": "拉面店"}]}

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"spatial_search": AsyncMock(return_value=mock_metadata)},
    ):
        results = await _execute_tasks(tasks)

    assert len(results) == 1
    key = next(iter(results))
    assert "#" not in key  # 无拆分后缀
    assert results[key].content == mock_metadata.payload
    assert results[key].tool_name == "spatial_search"


# =============================================================================
# P0 — search_node web_search 端到端拆分
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_node_splits_web_search_in_query_results():
    """search_node 执行 web_search → query_results 中每条为独立 key。"""
    from src.agent.nodes.research.search.node import search_node

    tasks = [
        SearchTask(
            tool_name="web_search",
            dimension="attraction",
            parameters={"query": "京都红叶", "max_results": 3},
            rationale="测试端到端拆分",
        ),
    ]
    manifest = ResearchManifest(loop_state=ResearchLoopInternal(active_queries=tasks))

    mock_metadata = AsyncMock()
    mock_metadata.payload = {
        "query": "京都红叶",
        "total": 2,
        "results": [
            {"title": "永观堂", "url": "https://a.com/1", "snippet": "s1", "content": "美景", "crawl_status": "success"},
            {"title": "清水寺", "url": "https://a.com/2", "snippet": "s2", "content": "绝美", "crawl_status": "success"},
        ],
    }

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"web_search": AsyncMock(return_value=mock_metadata)},
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    query_results = new_manifest.loop_state.query_results
    assert len(query_results) == 2
    for key, rr in query_results.items():
        assert "#" in key
        assert isinstance(rr, ResearchResult)
        assert rr.tool_name == "web_search"
        assert "url" in rr.content


# =============================================================================
# P0 — search_node
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_node_missing_research_data():
    """无 research_data → SKIPPED trace。"""
    from src.agent.nodes.research.search.node import search_node

    state = {"messages": []}
    result = await search_node(state)

    traces = result.get("trace_history", [])
    assert len(traces) == 1
    assert traces[0].status == "SKIPPED"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_node_empty_active_queries():
    """空 active_queries → SUCCESS trace，不执行任何工具。"""
    from src.agent.nodes.research.search.node import search_node

    manifest = ResearchManifest()
    state = {"research_data": manifest, "messages": []}

    result = await search_node(state)

    traces = result.get("trace_history", [])
    assert traces[0].status == "SUCCESS"
    assert traces[0].detail["task_count"] == 0


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_node_writes_to_loop_state():
    """正常流程: 结果写入 loop_state.query_results，清空 active_queries。"""
    from src.agent.nodes.research.search.node import search_node

    tasks = [
        SearchTask(
            tool_name="mock_tool",
            dimension="attraction",
            parameters={"keyword": "浅草"},
            rationale="测试 loop_state 写入",
        )
    ]
    manifest = ResearchManifest(loop_state=ResearchLoopInternal(active_queries=tasks))

    mock_metadata = AsyncMock()
    mock_metadata.payload = {"pois": [{"name": "浅草寺"}]}

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"mock_tool": AsyncMock(return_value=mock_metadata)},
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    # active_queries 已清空
    assert new_manifest.loop_state.active_queries == []
    # loop_state.query_results 已写入
    assert new_manifest.loop_state is not None
    assert len(new_manifest.loop_state.query_results) == 1
    # trace 正确
    traces = result["trace_history"]
    assert traces[0].status == "SUCCESS"
    assert traces[0].detail["executed_tasks"] == 1
    assert traces[0].detail["collected_results"] == 1


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_search_node_preserves_existing_loop_state():
    """已有 loop_state 字段时，model_copy 不丢弃已有数据。"""
    from src.agent.nodes.research.search.node import search_node

    tasks = [
        SearchTask(
            tool_name="mock_tool",
            dimension="dining",
            parameters={"keyword": "拉面"},
            rationale="测试状态保留",
        )
    ]
    existing_loop = ResearchLoopInternal(
        all_passed_results=[],
        loop_iteration=1,
        active_queries=tasks,
    )
    manifest = ResearchManifest(loop_state=existing_loop)

    mock_metadata = AsyncMock()
    mock_metadata.payload = {"pois": [{"name": "一兰拉面"}]}

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"mock_tool": AsyncMock(return_value=mock_metadata)},
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    # loop_state 保留了原有字段 (loop_iter 未被重置)
    assert new_manifest.loop_state.loop_iteration == 1
    # 同时写入了 query_results
    assert len(new_manifest.loop_state.query_results) == 1


# =============================================================================
# P0 — 文档/非文档分流
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_node_splits_doc_from_non_doc():
    """文档结果 → passed_doc_ids；非文档结果 → query_results。"""
    from src.agent.nodes.research.search.node import search_node

    tasks = [
        SearchTask(
            tool_name="document_search",
            dimension="attraction",
            parameters={"query": "函馆夜景"},
            rationale="test",
        ),
        SearchTask(
            tool_name="spatial_search",
            dimension="dining",
            parameters={"center": "函馆", "radius_m": "2000"},
            rationale="test",
        ),
    ]
    manifest = ResearchManifest(loop_state=ResearchLoopInternal(active_queries=tasks))

    mock_doc_result = AsyncMock()
    mock_doc_result.payload = {
        "query": "函馆夜景",
        "docs": [
            {"doc_id": "doc_abc123", "title": "函馆夜景攻略", "score": 3.5},
            {"doc_id": "doc_def456", "title": "北海道三大夜景", "score": 2.8},
        ],
    }
    mock_spatial_result = AsyncMock()
    mock_spatial_result.payload = {
        "pois": [{"name": "幸运小丑汉堡", "category": "restaurant"}],
    }

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {
            "document_search": AsyncMock(return_value=mock_doc_result),
            "spatial_search": AsyncMock(return_value=mock_spatial_result),
        },
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    # 非文档结果在 query_results
    assert len(new_manifest.loop_state.query_results) == 1
    assert "doc_abc123" not in str(new_manifest.loop_state.query_results)
    # 文档 doc_id 在 passed_doc_ids
    assert len(new_manifest.loop_state.passed_doc_ids) == 2
    assert "doc_abc123" in new_manifest.loop_state.passed_doc_ids
    assert "doc_def456" in new_manifest.loop_state.passed_doc_ids
    # active_queries 已清空
    assert new_manifest.loop_state.active_queries == []


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_node_doc_results_accumulate():
    """passed_doc_ids 跨迭代累积，不覆盖已有 doc_id。"""
    from src.agent.nodes.research.search.node import search_node

    tasks = [
        SearchTask(
            tool_name="document_search",
            dimension="attraction",
            parameters={"query": "京都寺庙"},
            rationale="test",
        ),
    ]
    existing_loop = ResearchLoopInternal(
        active_queries=tasks,
        passed_doc_ids=["doc_existing_1", "doc_existing_2"],
    )
    manifest = ResearchManifest(loop_state=existing_loop)

    mock_doc_result = AsyncMock()
    mock_doc_result.payload = {
        "query": "京都寺庙",
        "docs": [
            {"doc_id": "doc_new_1", "title": "金阁寺", "score": 4.0},
            {"doc_id": "doc_existing_1", "title": "清水寺", "score": 3.5},  # 重复的
        ],
    }

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"document_search": AsyncMock(return_value=mock_doc_result)},
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    doc_ids = new_manifest.loop_state.passed_doc_ids
    # 保留已有
    assert "doc_existing_1" in doc_ids
    assert "doc_existing_2" in doc_ids
    # 新增
    assert "doc_new_1" in doc_ids
    # 无重复
    assert len(doc_ids) == 3


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_search_node_empty_doc_results():
    """document_search 无结果时 passed_doc_ids 保持不变。"""
    from src.agent.nodes.research.search.node import search_node

    tasks = [
        SearchTask(
            tool_name="document_search",
            dimension="attraction",
            parameters={"query": "不存在的内容"},
            rationale="test",
        ),
    ]
    existing_loop = ResearchLoopInternal(
        active_queries=tasks,
        passed_doc_ids=["doc_keep_me"],
    )
    manifest = ResearchManifest(loop_state=existing_loop)

    mock_doc_result = AsyncMock()
    mock_doc_result.payload = {"query": "不存在的内容", "docs": []}

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"document_search": AsyncMock(return_value=mock_doc_result)},
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    # passed_doc_ids 保持不变
    assert new_manifest.loop_state.passed_doc_ids == ["doc_keep_me"]


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_search_node_only_non_doc_results():
    """仅有非文档工具时 passed_doc_ids 不被修改。"""
    from src.agent.nodes.research.search.node import search_node

    tasks = [
        SearchTask(
            tool_name="spatial_search",
            dimension="dining",
            parameters={"center": "东京", "radius_m": "1000"},
            rationale="test",
        ),
    ]
    existing_loop = ResearchLoopInternal(
        active_queries=tasks,
        passed_doc_ids=["doc_preexisting"],
    )
    manifest = ResearchManifest(loop_state=existing_loop)

    mock_result = AsyncMock()
    mock_result.payload = {"pois": [{"name": "一兰拉面"}]}

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"spatial_search": AsyncMock(return_value=mock_result)},
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    # query_results 有非文档结果
    assert len(new_manifest.loop_state.query_results) == 1
    # passed_doc_ids 不受影响
    assert new_manifest.loop_state.passed_doc_ids == ["doc_preexisting"]
