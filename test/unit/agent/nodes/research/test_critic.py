"""
Test Suite: Critic Node
Mapping: /src/agent/nodes/research/critic.py
Priority: P0 - Research Loop quality gate
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.agent.state.schema import (
    CriticResult,
    LoopSummary,
    ResearchLoopInternal,
    ResearchManifest,
    ResearchResult,
)


# =============================================================================
# P0 — Layer 1: 黑名单过滤
# =============================================================================


@pytest.mark.priority("P0")
def test_blacklist_filter_hit():
    """黑名单命中 → 结果被拒绝，未命中 → 通过。"""
    from src.agent.nodes.research.critic.node import blacklist_filter

    results = {
        "q1": ResearchResult(
            tool_name="spatial_search",
            query="东京酒店",
            content_type="json",
            content={},
            content_summary="东京新宿附近有多家五星级酒店",
        ),
        "q2": ResearchResult(
            tool_name="spatial_search",
            query="test",
            content_type="text",
            content={},
            content_summary="涉及暴力内容的非法信息",
        ),
    }
    blacklist = ["暴力", "色情", "赌博"]

    passed, rejected = blacklist_filter(results, blacklist)

    assert "q1" in passed
    assert "q2" in rejected
    assert "暴力" in rejected["q2"]
    assert len(passed) == 1
    assert len(rejected) == 1


@pytest.mark.priority("P1")
def test_blacklist_filter_all_pass():
    """所有结果均不命中黑名单 → 全部通过。"""
    from src.agent.nodes.research.critic.node import blacklist_filter

    results = {
        "q1": ResearchResult(
            tool_name="spatial_search",
            query="大阪美食",
            content_type="json",
            content={},
            content_summary="道顿堀附近评分4.5以上的拉面店",
        ),
    }
    blacklist = ["暴力", "赌博"]

    passed, rejected = blacklist_filter(results, blacklist)

    assert "q1" in passed
    assert len(rejected) == 0


@pytest.mark.priority("P1")
def test_blacklist_filter_case_insensitive():
    """黑名单匹配不区分大小写。"""
    from src.agent.nodes.research.critic.node import blacklist_filter

    results = {
        "q1": ResearchResult(
            tool_name="spatial_search",
            query="test",
            content_type="text",
            content={},
            content_summary="Some VIOLENCE related content here",
        ),
    }
    blacklist = ["violence"]

    passed, rejected = blacklist_filter(results, blacklist)

    assert "q1" in rejected


# =============================================================================
# P0 — Layer 3: 分数阈值过滤
# =============================================================================


@pytest.mark.priority("P0")
def test_code_filter_unsafe_tag():
    """safety_tag=unsafe → 直接拒绝。"""
    from src.agent.nodes.research.critic.node import code_filter

    results = [
        CriticResult(
            query="test",
            safety_tag="unsafe",
            relevance_score=90.0,
            utility_score=90.0,
            rationale="包含违规内容",
        ),
        CriticResult(
            query="test2",
            safety_tag="safe",
            relevance_score=85.0,
            utility_score=80.0,
            rationale="正常内容",
        ),
    ]

    passed, rejected = code_filter(results)

    assert len(passed) == 1
    assert passed[0].safety_tag == "safe"
    assert len(rejected) == 1
    assert rejected[0].safety_tag == "unsafe"


@pytest.mark.priority("P0")
def test_code_filter_low_relevance():
    """relevance_score < 60 → 拒绝。"""
    from src.agent.nodes.research.critic.node import code_filter

    results = [
        CriticResult(
            query="test",
            safety_tag="safe",
            relevance_score=55.0,
            utility_score=80.0,
            rationale="不太相关",
        ),
    ]

    passed, rejected = code_filter(results)

    assert len(passed) == 0
    assert len(rejected) == 1


@pytest.mark.priority("P0")
def test_code_filter_low_utility():
    """utility_score < 60 → 拒绝。"""
    from src.agent.nodes.research.critic.node import code_filter

    results = [
        CriticResult(
            query="test",
            safety_tag="safe",
            relevance_score=75.0,
            utility_score=40.0,
            rationale="没有实用价值",
        ),
    ]

    passed, rejected = code_filter(results)

    assert len(passed) == 0
    assert len(rejected) == 1


@pytest.mark.priority("P1")
def test_code_filter_all_pass():
    """所有分数和 tag 均达标 → 全部通过。"""
    from src.agent.nodes.research.critic.node import code_filter

    results = [
        CriticResult(
            query="q1",
            safety_tag="safe",
            relevance_score=90.0,
            utility_score=85.0,
            rationale="精确匹配",
        ),
        CriticResult(
            query="q2",
            safety_tag="safe",
            relevance_score=70.0,
            utility_score=65.0,
            rationale="部分相关",
        ),
    ]

    passed, rejected = code_filter(results)

    assert len(passed) == 2
    assert len(rejected) == 0


# =============================================================================
# P0 — 循环退出决策
# =============================================================================


@pytest.mark.priority("P0")
def test_should_continue_loop_enough_passed_and_llm_false():
    """pass_count >= MIN 且 LLM 认为充分 → 退出循环。"""
    from src.agent.nodes.research.critic.node import should_continue_loop

    continue_loop, reason = should_continue_loop(
        pass_count=4, llm_continue_loop=False, loop_iter=1
    )

    assert continue_loop is False
    assert "通过" in reason


@pytest.mark.priority("P0")
def test_should_continue_loop_not_enough_passed():
    """pass_count 不达标 → 继续循环，即使 LLM 认为充分。"""
    from src.agent.nodes.research.critic.node import should_continue_loop

    continue_loop, reason = should_continue_loop(
        pass_count=1, llm_continue_loop=False, loop_iter=1
    )

    assert continue_loop is True


@pytest.mark.priority("P0")
def test_should_continue_loop_max_loops_exceeded():
    """达到 MAX_LOOPS 硬上限 → 强制退出。"""
    from src.agent.nodes.research.critic.node import should_continue_loop

    continue_loop, reason = should_continue_loop(
        pass_count=1, llm_continue_loop=True, loop_iter=3
    )

    assert continue_loop is False
    assert "最大迭代轮次" in reason


@pytest.mark.priority("P1")
def test_should_continue_loop_llm_wants_more():
    """LLM 要求继续 → 继续循环（即使 pass_count 达标）。"""
    from src.agent.nodes.research.critic.node import should_continue_loop

    continue_loop, reason = should_continue_loop(
        pass_count=5, llm_continue_loop=True, loop_iter=1
    )

    assert continue_loop is True


# =============================================================================
# P1 — 聚合统计
# =============================================================================


@pytest.mark.priority("P1")
def test_aggregate_loop_summary():
    """验证统计值计算正确。"""
    from src.agent.nodes.research.critic.node import aggregate_loop_summary

    passed = [
        CriticResult(
            query="q1",
            safety_tag="safe",
            relevance_score=90.0,
            utility_score=80.0,
            rationale="好",
        ),
        CriticResult(
            query="q2",
            safety_tag="safe",
            relevance_score=70.0,
            utility_score=60.0,
            rationale="还行",
        ),
    ]

    summary = aggregate_loop_summary(passed, total_count=5)

    assert summary.pass_count == 2
    assert summary.total_count == 5
    assert summary.avg_relevance == 80.0
    assert summary.avg_utility == 70.0


@pytest.mark.priority("P2")
def test_aggregate_loop_summary_empty():
    """空列表 → 各项均为 0。"""
    from src.agent.nodes.research.critic.node import aggregate_loop_summary

    summary = aggregate_loop_summary([], total_count=3)

    assert summary.pass_count == 0
    assert summary.avg_relevance == 0.0
    assert summary.avg_utility == 0.0


# =============================================================================
# P0 — 黑名单 YAML 加载
# =============================================================================


@pytest.mark.priority("P1")
def test_load_blacklist_returns_list():
    """YAML 文件加载成功且包含关键词。"""
    from src.agent.nodes.research.critic.node import load_blacklist

    blacklist = load_blacklist()

    assert isinstance(blacklist, list)
    assert len(blacklist) > 0
    assert "暴力" in blacklist
    assert "violence" in blacklist


# =============================================================================
# P0 — critic_node 主流程（mock LLM）
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_critic_node_empty_results_skips():
    """query_results 为空 → 直接跳过，返回 SKIPPED trace。"""
    from src.agent.nodes.research.critic.node import critic_node

    loop_state = ResearchLoopInternal(query_results={})
    manifest = ResearchManifest(loop_state=loop_state)
    state = {
        "research_data": manifest,
    }

    result = await critic_node(state)

    traces = result.get("trace_history", [])
    assert len(traces) == 1
    assert traces[0].status == "SKIPPED"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_critic_node_full_pipeline():
    """完整三层过滤管线：Layer1 黑名单 → Layer2 mock LLM → Layer3 阈值过滤。"""
    from src.agent.nodes.research.critic.node import critic_node

    # 准备 2 条结果: 1 条正常，1 条含黑名单关键词
    loop_state = ResearchLoopInternal(
        query_results={
            "正常查询": ResearchResult(
                tool_name="spatial_search",
                query="东京酒店推荐",
                content_type="json",
                content={"hotels": ["A", "B"]},
                content_summary="新宿附近多家高分酒店，含价格和地址",
            ),
            "违规查询": ResearchResult(
                tool_name="web_search",
                query="暴力事件",
                content_type="text",
                content={},
                content_summary="涉及暴力内容的详细描述",
            ),
        }
    )
    manifest = ResearchManifest(loop_state=loop_state)
    state = {"research_data": manifest}

    # Mock Layer 2 LLM 返回正常评分
    mock_critic_results = [
        CriticResult(
            query="东京酒店推荐",
            safety_tag="safe",
            relevance_score=90.0,
            utility_score=85.0,
            rationale="精确匹配酒店需求",
        ),
    ]

    with patch(
        "src.agent.nodes.research.critic.node.llm_score_batch",
        new=AsyncMock(return_value=(mock_critic_results, False, "已充分")),
    ):
        result = await critic_node(state)

    new_manifest = result["research_data"]
    new_loop = new_manifest.loop_state

    # 黑名单过滤: 1 条通过 → Layer2 评分 → Layer3 通过
    assert len(new_loop.passed_results) == 1
    assert new_loop.passed_results[0].query == "东京酒店推荐"

    # 累计通过
    assert len(new_loop.all_passed_results) == 1

    # passed_queries 已记录
    assert "东京酒店推荐" in new_loop.passed_queries

    # LLM 返回 continue_loop=False 且 pass_count=1 < PASS_COUNT_MIN(3) → 仍继续
    assert new_loop.continue_loop is True

    # loop_iteration 已递增
    assert new_loop.loop_iteration == 1

    # loop_summary 已生成
    assert new_loop.loop_summary is not None
    assert new_loop.loop_summary.total_count == 2
    assert new_loop.loop_summary.pass_count == 1

    # trace 已写入
    traces = result.get("trace_history", [])
    assert len(traces) == 1
    assert traces[0].status == "SUCCESS"


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_critic_node_llm_error_graceful():
    """Layer 2 LLM 调用失败 → 不中断流程，继续处理。"""
    from src.agent.nodes.research.critic.node import critic_node

    loop_state = ResearchLoopInternal(
        query_results={
            "test_query": ResearchResult(
                tool_name="spatial_search",
                query="测试",
                content_type="json",
                content={},
                content_summary="正常内容",
            ),
        }
    )
    manifest = ResearchManifest(loop_state=loop_state)
    state = {"research_data": manifest}

    # Mock LLM 抛出异常
    with patch(
        "src.agent.nodes.research.critic.node.llm_score_batch",
        new=AsyncMock(side_effect=Exception("LLM timeout")),
    ):
        result = await critic_node(state)

    # 不应崩溃
    new_loop = result["research_data"].loop_state
    assert new_loop.passed_results == []
    assert new_loop.continue_loop is True  # 0 条通过 < 3
    traces = result.get("trace_history", [])
    assert traces[0].status == "SUCCESS"


@pytest.mark.priority("P2")
@pytest.mark.asyncio
async def test_critic_node_accumulates_all_passed():
    """多轮调用间 all_passed_results 正确累积。"""
    from src.agent.nodes.research.critic.node import critic_node

    # 模拟第二轮: 已有历史通过结果
    previous_passed = [
        CriticResult(
            query="历史查询",
            safety_tag="safe",
            relevance_score=80.0,
            utility_score=75.0,
            rationale="历史结果",
        ),
    ]
    loop_state = ResearchLoopInternal(
        query_results={
            "新查询": ResearchResult(
                tool_name="spatial_search",
                query="新查询",
                content_type="json",
                content={},
                content_summary="新结果",
            ),
        },
        all_passed_results=previous_passed,
    )
    manifest = ResearchManifest(loop_state=loop_state)
    state = {"research_data": manifest}

    mock_results = [
        CriticResult(
            query="新查询",
            safety_tag="safe",
            relevance_score=85.0,
            utility_score=80.0,
            rationale="新结果评估",
        ),
    ]

    with patch(
        "src.agent.nodes.research.critic.node.llm_score_batch",
        new=AsyncMock(return_value=(mock_results, False, "done")),
    ):
        result = await critic_node(state)

    all_passed = result["research_data"].loop_state.all_passed_results
    assert len(all_passed) == 2
    queries = [r.query for r in all_passed]
    assert "历史查询" in queries
    assert "新查询" in queries
