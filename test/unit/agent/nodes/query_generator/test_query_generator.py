"""
Test Suite: QueryGenerator Node
Mapping: /src/agent/nodes/query_generator/node.py
Priority: P0 — Research Loop task generation gate
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.agent.state import ResearchManifest, SearchTask, QueryGeneratorOutput
from src.agent.state.schema import ResearchLoopInternal


# =============================================================================
# P0 — prompt injection (feedback + passed_queries)
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_qg_injects_feedback_into_prompt():
    """Critic 反馈被注入到 LLM prompt 中。"""
    from src.agent.nodes.research.query_generator.node import query_generator_node

    loop_state = ResearchLoopInternal(feedback="需要补充交通维度的调研")
    manifest = ResearchManifest(loop_state=loop_state)
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "东京三日游",
    }

    mock_llm = MagicMock()
    mock_llm.content = json.dumps({
        "tasks": [{
            "tool_name": "spatial_search",
            "dimension": "transportation",
            "parameters": {"keyword": "东京地铁"},
            "rationale": "补充交通维度",
        }],
        "research_strategy": "补充交通维度调研",
    })

    with patch(
        "src.agent.nodes.research.query_generator.node.LLMFactory.get_model",
        return_value=MagicMock(bind=MagicMock(return_value=MagicMock(ainvoke=AsyncMock(return_value=mock_llm)))),
    ):
        result = await query_generator_node(state)

    new_manifest = result["research_data"]
    assert len(new_manifest.loop_state.active_queries) == 1
    assert new_manifest.loop_state.active_queries[0].dimension == "transportation"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_qg_injects_passed_queries_into_prompt():
    """已通过查询列表被注入到 LLM prompt 中（prompt 中可见）。"""
    from src.agent.nodes.research.query_generator.node import query_generator_node

    passed_queries = [
        '{"keyword": "东京酒店"}',
        '{"keyword": "浅草寺"}',
    ]
    loop_state = ResearchLoopInternal(passed_queries=passed_queries)
    manifest = ResearchManifest(loop_state=loop_state)
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "东京三日游",
    }

    captured_prompt = []

    class FakeLLM:
        content = json.dumps({
            "tasks": [],
            "research_strategy": "所有查询已覆盖",
        })

    mock_llm = FakeLLM()

    def capture_prompt(prompt_str):
        captured_prompt.append(prompt_str)
        return mock_llm

    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(side_effect=capture_prompt)

    with patch(
        "src.agent.nodes.research.query_generator.node.LLMFactory.get_model",
        return_value=MagicMock(bind=MagicMock(return_value=mock_bound)),
    ):
        await query_generator_node(state)

    prompt = captured_prompt[0]
    assert "东京酒店" in prompt or '"keyword": "东京酒店"' in prompt
    assert "浅草寺" in prompt or '"keyword": "浅草寺"' in prompt


# =============================================================================
# P0 — ResearchManifest model_copy preservation
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_qg_preserves_loop_state():
    """model_copy 保留已有 loop_state（feedback、passed_queries 等不丢失）。"""
    from src.agent.nodes.research.query_generator.node import query_generator_node

    loop_state = ResearchLoopInternal(
        feedback="上次反馈",
        passed_queries=["旧查询"],
        loop_iteration=2,
        all_passed_results=[],
    )
    manifest = ResearchManifest(loop_state=loop_state)
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "第三次调研",
    }

    mock_llm = MagicMock()
    mock_llm.content = json.dumps({
        "tasks": [{
            "tool_name": "spatial_search",
            "dimension": "dining",
            "parameters": {"keyword": "新拉面"},
            "rationale": "新维度",
        }],
        "research_strategy": "继续拓展",
    })

    with patch(
        "src.agent.nodes.research.query_generator.node.LLMFactory.get_model",
        return_value=MagicMock(bind=MagicMock(return_value=MagicMock(ainvoke=AsyncMock(return_value=mock_llm)))),
    ):
        result = await query_generator_node(state)

    new_manifest = result["research_data"]
    assert new_manifest.loop_state.feedback == "上次反馈"
    assert new_manifest.loop_state.passed_queries == ["旧查询"]
    assert new_manifest.loop_state.loop_iteration == 2


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_qg_preserves_research_hashes():
    """model_copy 保留已有 research_hashes。"""
    from src.agent.nodes.research.query_generator.node import query_generator_node

    existing_hashes = {"东京酒店": ["hash_abc123"], "大阪美食": ["hash_def456"]}
    manifest = ResearchManifest(research_hashes=existing_hashes)
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "再查一次",
    }

    mock_llm = MagicMock()
    mock_llm.content = json.dumps({
        "tasks": [{
            "tool_name": "route_search",
            "dimension": "transportation",
            "parameters": {"mode": "shortest", "origin": "东京站", "destination": "新宿站"},
            "rationale": "交通补充",
        }],
        "research_strategy": "补充交通",
    })

    with patch(
        "src.agent.nodes.research.query_generator.node.LLMFactory.get_model",
        return_value=MagicMock(bind=MagicMock(return_value=MagicMock(ainvoke=AsyncMock(return_value=mock_llm)))),
    ):
        result = await query_generator_node(state)

    new_manifest = result["research_data"]
    assert new_manifest.research_hashes == existing_hashes


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_qg_appends_research_history():
    """每次调用在 research_history 末尾追加当前 user_request。"""
    from src.agent.nodes.research.query_generator.node import query_generator_node

    manifest = ResearchManifest(research_history=["第一次查东京", "第二次查大阪"])
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "第三次查京都",
    }

    mock_llm = MagicMock()
    mock_llm.content = json.dumps({
        "tasks": [],
        "research_strategy": "无需新查询",
    })

    with patch(
        "src.agent.nodes.research.query_generator.node.LLMFactory.get_model",
        return_value=MagicMock(bind=MagicMock(return_value=MagicMock(ainvoke=AsyncMock(return_value=mock_llm)))),
    ):
        result = await query_generator_node(state)

    new_manifest = result["research_data"]
    assert new_manifest.research_history == ["第一次查东京", "第二次查大阪", "第三次查京都"]


# =============================================================================
# P0 — new ResearchManifest when none exists
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_qg_creates_manifest_when_none():
    """无 research_data 时创建新 ResearchManifest。"""
    from src.agent.nodes.research.query_generator.node import query_generator_node

    state = {
        "messages": [],
        "user_request": "大阪一日游",
    }

    mock_llm = MagicMock()
    mock_llm.content = json.dumps({
        "tasks": [{
            "tool_name": "spatial_search",
            "dimension": "attraction",
            "parameters": {"keyword": "大阪城"},
            "rationale": "首轮调研",
        }],
        "research_strategy": "基础景点调研",
    })

    with patch(
        "src.agent.nodes.research.query_generator.node.LLMFactory.get_model",
        return_value=MagicMock(bind=MagicMock(return_value=MagicMock(ainvoke=AsyncMock(return_value=mock_llm)))),
    ):
        result = await query_generator_node(state)

    new_manifest = result["research_data"]
    assert isinstance(new_manifest, ResearchManifest)
    assert len(new_manifest.loop_state.active_queries) == 1
    assert new_manifest.research_history == ["大阪一日游"]


# =============================================================================
# P1 — edge cases
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_qg_empty_feedback_and_passed_queries():
    """首轮调研：feedback 和 passed_queries 均为空时使用默认占位文本。"""
    from src.agent.nodes.research.query_generator.node import query_generator_node

    manifest = ResearchManifest()
    state = {
        "research_data": manifest,
        "messages": [],
        "user_request": "北海道滑雪",
    }

    captured_prompt = []

    class FakeLLM:
        content = json.dumps({
            "tasks": [],
            "research_strategy": "首轮",
        })

    mock_bound = MagicMock()
    mock_bound.ainvoke = AsyncMock(side_effect=lambda p: captured_prompt.append(p) or FakeLLM())

    with patch(
        "src.agent.nodes.research.query_generator.node.LLMFactory.get_model",
        return_value=MagicMock(bind=MagicMock(return_value=mock_bound)),
    ):
        await query_generator_node(state)

    prompt = captured_prompt[0]
    assert "无（首轮调研）" in prompt


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_qg_llm_error_graceful():
    """LLM 调用失败时返回 FAIL trace，不崩溃。"""
    from src.agent.nodes.research.query_generator.node import query_generator_node

    state = {
        "research_data": ResearchManifest(),
        "messages": [],
        "user_request": "测试",
    }

    with patch(
        "src.agent.nodes.research.query_generator.node.LLMFactory.get_model",
        return_value=MagicMock(
            bind=MagicMock(
                return_value=MagicMock(ainvoke=AsyncMock(side_effect=RuntimeError("LLM 超时")))
            )
        ),
    ):
        result = await query_generator_node(state)

    traces = result.get("trace_history", [])
    assert len(traces) == 1
    assert traces[0].status == "FAIL"
    assert "LLM 超时" in traces[0].detail["error"]


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_qg_content_list_merge():
    """LLM 返回 content 为 list 时正确合并。"""
    from src.agent.nodes.research.query_generator.node import query_generator_node

    state = {
        "research_data": ResearchManifest(),
        "messages": [],
        "user_request": "测试",
    }

    task_json = json.dumps({
        "tasks": [],
        "research_strategy": "list 合并测试",
    })
    mock_llm = MagicMock()
    mock_llm.content = [{"text": task_json}]

    with patch(
        "src.agent.nodes.research.query_generator.node.LLMFactory.get_model",
        return_value=MagicMock(bind=MagicMock(return_value=MagicMock(ainvoke=AsyncMock(return_value=mock_llm)))),
    ):
        result = await query_generator_node(state)

    assert result["trace_history"][0].status == "SUCCESS"
