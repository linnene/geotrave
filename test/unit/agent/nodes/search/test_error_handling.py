"""
Test Suite: Error Handling — L0 filter, FetchError classification, blacklist/hash protection
Mapping: /src/crawler/, /src/agent/nodes/research/search/node.py,
         /src/agent/nodes/research/critic/node.py,
         /src/agent/nodes/research/hash/node.py
Priority: P0 — 系统稳定性
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agent.state import SearchTask, ResearchManifest
from src.agent.state.schema import ResearchLoopInternal, ResearchResult


# =============================================================================
# P0 — L0 错误过滤器（Search 节点）
# =============================================================================


@pytest.mark.priority("P0")
def test_is_error_result_detects_error_envelope():
    """_is_error_result: content 含 error key 的 ResearchResult → True。"""
    from src.agent.nodes.research.search.node import _is_error_result

    error_rr = ResearchResult(
        tool_name="web_search",
        query="test",
        content_type="json",
        content={"error": "Connection refused"},
        content_summary="执行失败: Connection refused",
    )
    assert _is_error_result(error_rr) is True


@pytest.mark.priority("P0")
def test_is_error_result_normal_result_returns_false():
    """_is_error_result: 正常 content（无 error key）→ False。"""
    from src.agent.nodes.research.search.node import _is_error_result

    normal_rr = ResearchResult(
        tool_name="spatial_search",
        query="test",
        content_type="json",
        content={"pois": [{"name": "东京塔"}]},
        content_summary="POI: 东京塔",
    )
    assert _is_error_result(normal_rr) is False


@pytest.mark.priority("P0")
def test_is_error_result_non_dict_content_returns_false():
    """_is_error_result: content 非 dict（如字符串/列表）→ False。"""
    from src.agent.nodes.research.search.node import _is_error_result

    str_rr = ResearchResult(
        tool_name="web_search",
        query="test",
        content_type="text",
        content="some text content",
        content_summary="text summary",
    )
    assert _is_error_result(str_rr) is False


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_error_envelope_filtered_out_of_query_results():
    """search_node: error 结果被 L0 过滤器拦截，不进入 loop_state.query_results。"""
    from src.agent.nodes.research.search.node import search_node

    tasks = [
        SearchTask(
            tool_name="broken_tool",
            dimension="attraction",
            parameters={"keyword": "东京塔"},
            rationale="test",
        )
    ]
    manifest = ResearchManifest(loop_state=ResearchLoopInternal(active_queries=tasks))

    async def broken_handler(task):
        raise RuntimeError("数据库连接超时")

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {"broken_tool": broken_handler},
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    # error 结果不应进入 query_results
    assert len(new_manifest.loop_state.query_results) == 0
    # trace 应记录 error_results_filtered
    traces = result["trace_history"]
    assert traces[0].detail["error_results_filtered"] == 1


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_l0_filter_mixed_with_valid_results():
    """search_node: error 与有效结果混合时，仅 error 被过滤，有效结果保留。"""
    from src.agent.nodes.research.search.node import search_node

    tasks = [
        SearchTask(
            tool_name="broken_tool",
            dimension="attraction",
            parameters={"keyword": "fail"},
            rationale="会失败",
        ),
        SearchTask(
            tool_name="good_tool",
            dimension="dining",
            parameters={"keyword": "拉面"},
            rationale="会成功",
        ),
    ]
    manifest = ResearchManifest(loop_state=ResearchLoopInternal(active_queries=tasks))

    async def broken_handler(task):
        raise RuntimeError("数据库连接超时")

    good_metadata = AsyncMock()
    good_metadata.payload = {"pois": [{"name": "一兰拉面"}]}

    with patch.dict(
        "src.agent.nodes.research.search.tools.TOOL_DISPATCH",
        {
            "broken_tool": broken_handler,
            "good_tool": AsyncMock(return_value=good_metadata),
        },
    ):
        result = await search_node({"research_data": manifest, "messages": []})

    new_manifest = result["research_data"]
    # 仅有效结果进入 query_results
    assert len(new_manifest.loop_state.query_results) == 1
    traces = result["trace_history"]
    assert traces[0].detail["error_results_filtered"] == 1
    assert traces[0].detail["collected_results"] == 2


# =============================================================================
# P0 — FetchError 分类（fetcher 层）
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_fetch_deep_antibot_raises_fetch_error():
    """fetch_deep: 反爬检测命中 → FetchError(error_code="blocked")。"""
    from src.crawler.schema import FetchError
    from src.crawler.fetcher import ContentFetcher

    fetcher = ContentFetcher(timeout=30)

    mock_result = MagicMock()
    mock_result.success = True
    mock_result.html = '<html><body>Please verify you\'re not a robot</body></html>'

    with patch.object(fetcher, "_crawler") as mock_crawler:
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        with pytest.raises(FetchError) as exc_info:
            await fetcher.fetch_deep("http://blocked-site.com/page")

    assert exc_info.value.error_code == "blocked"


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_fetch_deep_not_success_raises_fetch_error():
    """fetch_deep: result.success=False → FetchError，不返回 HTML。"""
    from src.crawler.schema import FetchError
    from src.crawler.fetcher import ContentFetcher

    fetcher = ContentFetcher(timeout=30)

    mock_result = MagicMock()
    mock_result.success = False
    mock_result.html = "<html>partial content</html>"
    mock_result.error_message = "ERR_BLOCKED_BY_CLIENT"

    with patch.object(fetcher, "_crawler") as mock_crawler:
        mock_crawler.arun = AsyncMock(return_value=mock_result)

        with pytest.raises(FetchError) as exc_info:
            await fetcher.fetch_deep("http://blocked-site.com/page")

    assert exc_info.value.error_code == "crawl_failed"
    assert "ERR_BLOCKED_BY_CLIENT" in exc_info.value.message


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_webcrawler_crawl_populates_error_code():
    """WebCrawler.crawl: fetch_fast 和 fetch_deep 都失败时，CrawlResult 携带 error_code。"""
    from src.crawler import WebCrawler
    from src.crawler.schema import FetchError

    crawler = WebCrawler(timeout=20)

    with patch.object(crawler.fetcher, "fetch_fast", side_effect=FetchError("timeout", "timed out")):
        with patch.object(crawler.fetcher, "fetch_deep", side_effect=FetchError("blocked", "anti-bot")):
            result = await crawler.crawl("http://bad-site.com/page")

    assert result.status == "error"
    assert result.error_code == "timeout"  # fast 失败先设置，deep 追加后保留第一个
    assert result.content is None


# =============================================================================
# P0 — 黑名单加载保护
# =============================================================================


@pytest.mark.priority("P0")
def test_load_blacklist_file_not_found():
    """load_blacklist: blacklist.yaml 缺失 → 返回空列表，不崩溃。"""
    from src.agent.nodes.research.critic.node import load_blacklist

    with patch("builtins.open", side_effect=FileNotFoundError):
        keywords = load_blacklist()

    assert keywords == []


@pytest.mark.priority("P1")
def test_load_blacklist_yaml_corrupted():
    """load_blacklist: YAML 解析失败 → 返回空列表，不崩溃。"""
    from src.agent.nodes.research.critic.node import load_blacklist

    with patch("builtins.open", MagicMock()):
        with patch("yaml.safe_load", side_effect=Exception("corrupted YAML")):
            keywords = load_blacklist()

        assert keywords == []


# =============================================================================
# P0 — Hash 节点 DB 写入保护
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_hash_node_db_failure_not_crashing():
    """hash_node: batch_store_results 失败 → 记录日志，不崩溃，不丢失 ExecutionSigns。"""
    from src.agent.nodes.research.hash.node import hash_node
    from src.agent.state.schema import CriticResult, ExecutionSigns

    passed = [
        CriticResult(
            query="test query",
            tool_name="web_search",
            safety_tag="safe",
            relevance_score=70,
            utility_score=65,
            rationale="测试",
            content_summary="test content",
        )
    ]
    loop_state = ResearchLoopInternal(all_passed_results=passed)
    manifest = ResearchManifest(loop_state=loop_state)

    state = {
        "research_data": manifest,
        "messages": [MagicMock(id="test_session_123")],
        "execution_signs": ExecutionSigns(is_safe=True, is_core_complete=True),
    }

    with patch(
        "src.agent.nodes.research.hash.node.batch_store_results",
        side_effect=RuntimeError("DB connection lost"),
    ):
        result = await hash_node(state)

    # 不崩溃
    assert "execution_signs" in result
    assert result["execution_signs"].is_loop_exit is True
    # 保留了原有的信号位
    assert result["execution_signs"].is_safe is True
    assert result["execution_signs"].is_core_complete is True
    # trace 仍然 SUCCESS（DB 失败不阻止流程）
    traces = result.get("trace_history", [])
    assert len(traces) >= 1
    assert traces[0].status == "SUCCESS"


# =============================================================================
# P1 — FetchError 超时分类
# =============================================================================


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_fetch_fast_timeout_raises_fetch_error():
    """fetch_fast: httpx.TimeoutException → FetchError(error_code="timeout")。"""
    import httpx
    from src.crawler.schema import FetchError
    from src.crawler.fetcher import ContentFetcher

    fetcher = ContentFetcher(timeout=30)

    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("timeout")):
        with pytest.raises(FetchError) as exc_info:
            await fetcher.fetch_fast("http://slow-site.com/page")

    assert exc_info.value.error_code == "timeout"


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_fetch_fast_http_4xx_raises_fetch_error():
    """fetch_fast: HTTP 403 → FetchError(error_code="http_4xx")。"""
    import httpx
    from src.crawler.schema import FetchError
    from src.crawler.fetcher import ContentFetcher

    fetcher = ContentFetcher(timeout=30)
    response = MagicMock()
    response.status_code = 403

    with patch("httpx.AsyncClient.get", side_effect=httpx.HTTPStatusError("403", request=MagicMock(), response=response)):
        with pytest.raises(FetchError) as exc_info:
            await fetcher.fetch_fast("http://forbidden.com/page")

    assert exc_info.value.error_code == "http_4xx"
