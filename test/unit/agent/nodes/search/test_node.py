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
    from src.agent.nodes.search.node import _generate_summary

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
    from src.agent.nodes.search.node import _generate_summary

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
    from src.agent.nodes.search.node import _generate_summary

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
    from src.agent.nodes.search.node import _generate_summary

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
    from src.agent.nodes.search.node import _generate_summary

    payload = {"custom_field": "custom_value", "nested": {"a": 1}}
    result = _generate_summary(payload)
    assert "custom_field" in result
    assert "custom_value" in result
    assert len(result) <= 500


# =============================================================================
# P0 — _execute_tasks
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_execute_tasks_wraps_in_research_result():
    """正常执行: 每个 task 结果包裹为 ResearchResult envelope。"""
    from src.agent.nodes.search.node import _execute_tasks

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
        "src.agent.nodes.search.tools.TOOL_DISPATCH",
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
    """未注册工具: 跳过并记录错误，不崩溃。"""
    from src.agent.nodes.search.node import _execute_tasks

    tasks = [
        SearchTask(
            tool_name="nonexistent_tool",
            dimension="general",
            parameters={},
            rationale="测试未注册工具",
        )
    ]

    with patch.dict("src.agent.nodes.search.tools.TOOL_DISPATCH", {}):
        results = await _execute_tasks(tasks)

    # 未注册工具被跳过，不产生结果
    assert len(results) == 0


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_execute_tasks_handler_exception():
    """handler 抛出异常: 返回 error envelope，不崩溃。"""
    from src.agent.nodes.search.node import _execute_tasks

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
        "src.agent.nodes.search.tools.TOOL_DISPATCH",
        {"broken_tool": broken_handler},
    ):
        results = await _execute_tasks(tasks)

    assert len(results) == 1
    envelope = next(iter(results.values()))
    assert isinstance(envelope, ResearchResult)
    assert "error" in envelope.content
    assert "执行失败" in envelope.content_summary
    assert envelope.tool_name == "broken_tool"


# =============================================================================
# P0 — search_node
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_node_missing_research_data():
    """无 research_data → SKIPPED trace。"""
    from src.agent.nodes.search.node import search_node

    state = {"messages": []}
    result = await search_node(state)

    traces = result.get("trace_history", [])
    assert len(traces) == 1
    assert traces[0].status == "SKIPPED"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_node_empty_active_queries():
    """空 active_queries → SUCCESS trace，不执行任何工具。"""
    from src.agent.nodes.search.node import search_node

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
    from src.agent.nodes.search.node import search_node

    tasks = [
        SearchTask(
            tool_name="mock_tool",
            dimension="attraction",
            parameters={"keyword": "浅草"},
            rationale="测试 loop_state 写入",
        )
    ]
    manifest = ResearchManifest(active_queries=tasks)

    mock_metadata = AsyncMock()
    mock_metadata.payload = {"pois": [{"name": "浅草寺"}]}

    with patch.dict(
        "src.agent.nodes.search.tools.TOOL_DISPATCH",
        {"mock_tool": AsyncMock(return_value=mock_metadata)},
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    # active_queries 已清空
    assert new_manifest.active_queries == []
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
    from src.agent.nodes.search.node import search_node

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
    )
    manifest = ResearchManifest(active_queries=tasks, loop_state=existing_loop)

    mock_metadata = AsyncMock()
    mock_metadata.payload = {"pois": [{"name": "一兰拉面"}]}

    with patch.dict(
        "src.agent.nodes.search.tools.TOOL_DISPATCH",
        {"mock_tool": AsyncMock(return_value=mock_metadata)},
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    # loop_state 保留了原有字段 (loop_iter 未被重置)
    assert new_manifest.loop_state.loop_iteration == 1
    # 同时写入了 query_results
    assert len(new_manifest.loop_state.query_results) == 1
