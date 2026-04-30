"""
Test Suite: DocumentManager — BM25 文档检索引擎
Mapping: /src/agent/nodes/research/search/docs/
Priority: P0 - Research Loop document retrieval engine
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# =============================================================================
# P0 — _tokenize
# =============================================================================


@pytest.mark.priority("P0")
def test_tokenize_chinese():
    """中文: 按字切分。"""
    from src.agent.nodes.research.search.docs.manager import _tokenize

    tokens = _tokenize("函馆夜景最佳观赏点")
    assert "函" in tokens
    assert "馆" in tokens
    assert "夜" in tokens
    assert "景" in tokens
    assert len(tokens) >= 8


@pytest.mark.priority("P0")
def test_tokenize_english():
    """英文: 按空格/标点分词并小写。"""
    from src.agent.nodes.research.search.docs.manager import _tokenize

    tokens = _tokenize("Best Cherry Blossom spots in Tokyo")
    assert "best" in tokens
    assert "cherry" in tokens
    assert "blossom" in tokens
    assert "tokyo" in tokens
    assert all(t == t.lower() for t in tokens if t.isascii())


@pytest.mark.priority("P0")
def test_tokenize_mixed_cn_en():
    """中英文混合: 英文按词、中文按字。"""
    from src.agent.nodes.research.search.docs.manager import _tokenize

    tokens = _tokenize("东京 Tokyo 塔")
    assert "东" in tokens
    assert "京" in tokens
    assert "tokyo" in tokens
    assert "塔" in tokens


@pytest.mark.priority("P1")
def test_tokenize_empty():
    """空字符串 → 空列表。"""
    from src.agent.nodes.research.search.docs.manager import _tokenize

    assert _tokenize("") == []
    assert _tokenize("   ") == []


# =============================================================================
# P0 — _gen_doc_id
# =============================================================================


@pytest.mark.priority("P0")
def test_gen_doc_id_deterministic():
    """相同内容 → 相同 doc_id。"""
    from src.agent.nodes.research.search.docs.manager import _gen_doc_id

    id1 = _gen_doc_id("函馆山夜景是日本三大夜景之一")
    id2 = _gen_doc_id("函馆山夜景是日本三大夜景之一")

    assert id1 == id2
    assert id1.startswith("doc_")
    assert len(id1) == 20  # "doc_" + 16 hex chars


@pytest.mark.priority("P0")
def test_gen_doc_id_different_content():
    """不同内容 → 不同 doc_id。"""
    from src.agent.nodes.research.search.docs.manager import _gen_doc_id

    id1 = _gen_doc_id("内容A")
    id2 = _gen_doc_id("内容B")

    assert id1 != id2


# =============================================================================
# Helpers
# =============================================================================


def _mock_pool_with_rows(rows):
    """构建返回指定行的 mock pool。"""
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = rows
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)
    return mock_pool


# =============================================================================
# P0 — DocumentManager.build_index
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_build_index_empty():
    """无系统文档 → 不构建 BM25 索引，is_loaded=False。"""
    from src.agent.nodes.research.search.docs.manager import DocumentManager

    mgr = DocumentManager()
    mock_pool = _mock_pool_with_rows([])

    await mgr.build_index(mock_pool)

    assert not mgr.is_loaded
    assert mgr.doc_count() == 0


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_build_index_with_docs():
    """有文档时: 构建 corpus 和元数据列表。"""
    from src.agent.nodes.research.search.docs.manager import DocumentManager

    mgr = DocumentManager()
    rows = [
        {
            "hash_key": "doc_abc123",
            "payload": {
                "title": "函馆夜景攻略",
                "place_name": "函馆",
                "content": "函馆山是观看夜景的最佳地点，建议黄昏时分上山。",
                "source": "test_source",
            },
        },
        {
            "hash_key": "doc_def456",
            "payload": {
                "title": "东京迪士尼指南",
                "place_name": "东京",
                "content": "东京迪士尼乐园是亚洲最受欢迎的主题公园之一。",
                "source": "test_source",
            },
        },
        {
            "hash_key": "doc_ghi789",
            "payload": {
                "title": "大阪环球影城",
                "place_name": "大阪",
                "content": "大阪环球影城是关西地区最大的主题乐园。",
                "source": "test_source",
            },
        },
        {
            "hash_key": "doc_jkl012",
            "payload": {
                "title": "京都清水寺",
                "place_name": "京都",
                "content": "清水寺是京都最古老的寺院，被列为世界文化遗产。",
                "source": "test_source",
            },
        },
    ]
    mock_pool = _mock_pool_with_rows(rows)

    await mgr.build_index(mock_pool)

    assert mgr.is_loaded
    assert mgr.doc_count() == 4


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_build_index_json_str_payload():
    """payload 为 JSON 字符串时正确解析。"""
    import json
    from src.agent.nodes.research.search.docs.manager import DocumentManager

    mgr = DocumentManager()
    payload_dict = {
        "title": "京都红叶",
        "place_name": "京都",
        "content": "岚山是京都赏红叶的最佳地点。",
        "source": "test",
    }
    rows = [
        {
            "hash_key": "doc_kyoto",
            "payload": json.dumps(payload_dict, ensure_ascii=False),
        },
        {
            "hash_key": "doc_osaka",
            "payload": {
                "title": "大阪城",
                "place_name": "大阪",
                "content": "大阪城是日本三名城之一。",
                "source": "test",
            },
        },
    ]
    mock_pool = _mock_pool_with_rows(rows)

    await mgr.build_index(mock_pool)

    assert mgr.doc_count() == 2


# =============================================================================
# P0 — DocumentManager.search
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_basic():
    """BM25 检索: 返回匹配文档的元数据（不含全文）。"""
    from src.agent.nodes.research.search.docs.manager import DocumentManager

    mgr = DocumentManager()
    rows = [
        {
            "hash_key": "doc_001",
            "payload": {
                "title": "札幌雪祭攻略",
                "place_name": "札幌",
                "content": "札幌雪祭是北海道最著名的冬季活动，每年二月在大通公园举行。",
                "source": "",
            },
        },
        {
            "hash_key": "doc_002",
            "payload": {
                "title": "冲绳海滩推荐",
                "place_name": "冲绳",
                "content": "冲绳的翡翠海滩以其碧蓝海水和白沙滩闻名。",
                "source": "",
            },
        },
        {
            "hash_key": "doc_003",
            "payload": {
                "title": "东京塔夜景",
                "place_name": "东京",
                "content": "东京塔是东京地标，夜晚亮灯后非常壮观。",
                "source": "",
            },
        },
        {
            "hash_key": "doc_004",
            "payload": {
                "title": "京都伏见稻荷",
                "place_name": "京都",
                "content": "伏见稻荷大社以千本鸟居闻名于世。",
                "source": "",
            },
        },
    ]
    mock_pool = _mock_pool_with_rows(rows)

    await mgr.build_index(mock_pool)

    results = mgr.search("札幌雪祭")
    assert len(results) > 0
    r = results[0]
    assert r["doc_id"] == "doc_001"
    assert r["title"] == "札幌雪祭攻略"
    assert r["place_name"] == "札幌"
    assert "score" in r
    assert "snippet" in r
    assert "content" not in r  # 不含全文


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_place_filter():
    """按地名过滤: 仅返回匹配 place_name 的文档。"""
    from src.agent.nodes.research.search.docs.manager import DocumentManager

    mgr = DocumentManager()
    rows = [
        {
            "hash_key": "doc_001",
            "payload": {
                "title": "大阪道顿堀餐厅探店",
                "place_name": "大阪",
                "content": "道顿堀是大阪最著名的美食街，汇集了众多餐厅和小吃。",
                "source": "",
            },
        },
        {
            "hash_key": "doc_002",
            "payload": {
                "title": "东京筑地市场指南",
                "place_name": "东京",
                "content": "筑地市场是东京著名的海鲜市场，新鲜寿司和刺身应有尽有。",
                "source": "",
            },
        },
        {
            "hash_key": "doc_003",
            "payload": {
                "title": "京都红叶名所",
                "place_name": "京都",
                "content": "岚山和清水寺是京都赏红叶的最佳地点。",
                "source": "",
            },
        },
        {
            "hash_key": "doc_004",
            "payload": {
                "title": "札幌雪祭攻略",
                "place_name": "札幌",
                "content": "札幌雪祭是北海道最著名的冬季活动。",
                "source": "",
            },
        },
    ]
    mock_pool = _mock_pool_with_rows(rows)

    await mgr.build_index(mock_pool)

    results = mgr.search("美食 餐厅", place_filter="大阪")
    assert len(results) > 0
    for r in results:
        assert "大阪" in (r["place_name"] or "")


@pytest.mark.priority("P0")
def test_search_empty_index():
    """未加载索引 → 返回空列表。"""
    from src.agent.nodes.research.search.docs.manager import DocumentManager

    mgr = DocumentManager()
    results = mgr.search("任何关键词")
    assert results == []


@pytest.mark.priority("P1")
def test_search_empty_query():
    """空 query → 返回空列表。"""
    from src.agent.nodes.research.search.docs.manager import DocumentManager

    mgr = DocumentManager()
    results = mgr.search("")
    assert results == []


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_search_score_threshold():
    """低相关度结果被 BM25_SCORE_THRESHOLD 过滤掉。"""
    from src.agent.nodes.research.search.docs.manager import DocumentManager

    mgr = DocumentManager()
    rows = [
        {
            "hash_key": "doc_001",
            "payload": {
                "title": "函馆夜景攻略",
                "place_name": "函馆",
                "content": "函馆山是观看夜景的最佳地点。",
                "source": "",
            },
        },
        {
            "hash_key": "doc_002",
            "payload": {
                "title": "东京旅游",
                "place_name": "东京",
                "content": "东京是日本的首都。",
                "source": "",
            },
        },
    ]
    mock_pool = _mock_pool_with_rows(rows)

    await mgr.build_index(mock_pool)

    results = mgr.search("函数式编程 微服务 架构设计")
    assert len(results) == 0


# =============================================================================
# P0 — DocumentManager.ingest
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_ingest():
    """ingest 写入 PostgreSQL + 增量更新内存索引。"""
    from src.agent.nodes.research.search.docs.manager import DocumentManager

    mgr = DocumentManager()
    # 先构建含 1 篇文档的索引
    doc_row = {
        "hash_key": "doc_init",
        "payload": {
            "title": "初始文档",
            "place_name": "测试",
            "content": "这是一篇初始文档内容包含测试字符。",
            "source": "",
        },
    }
    mock_pool = _mock_pool_with_rows([doc_row])
    await mgr.build_index(mock_pool)
    assert mgr.doc_count() == 1

    with patch(
        "src.database.retrieval_db.store_result",
        new=AsyncMock(),
    ) as mock_store:
        doc_id = await mgr.ingest(
            content="箱根温泉是关东地区最受欢迎的温泉胜地。",
            metadata={"title": "箱根温泉指南", "place_name": "箱根", "source": "test"},
            pool=mock_pool,
        )

    assert doc_id.startswith("doc_")
    mock_store.assert_awaited_once()
    assert mgr.doc_count() == 2


@pytest.mark.priority("P1")
@pytest.mark.asyncio
async def test_doc_count():
    """doc_count 返回索引中文档数量。"""
    from src.agent.nodes.research.search.docs.manager import DocumentManager

    mgr = DocumentManager()
    rows = [
        {
            "hash_key": f"doc_{i:03d}",
            "payload": {
                "title": f"文档{i}",
                "place_name": "测试",
                "content": f"这是第{i}篇测试文档的内容。",
                "source": "",
            },
        }
        for i in range(3)
    ]
    mock_pool = _mock_pool_with_rows(rows)

    await mgr.build_index(mock_pool)
    assert mgr.doc_count() == 3


# =============================================================================
# P0 — get_document_manager 单例
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_get_document_manager_singleton():
    """同一进程内多次调用返回同一实例。"""
    import src.agent.nodes.research.search.docs.manager as dm

    # 重置全局单例以隔离测试
    dm._document_manager = None

    doc_row = {
        "hash_key": "doc_init",
        "payload": {
            "title": "初始",
            "place_name": "测试",
            "content": "测试文档。",
            "source": "",
        },
    }
    mock_pool = _mock_pool_with_rows([doc_row])

    mgr1 = await dm.get_document_manager(mock_pool)
    mgr2 = await dm.get_document_manager(mock_pool)

    assert mgr1 is mgr2

    # 恢复单例
    dm._document_manager = None


# =============================================================================
# P0 — document_search tool handler
# =============================================================================


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_document_search_tool():
    """document_search 工具: 调用 DocumentManager.search 并返回 RetrievalMetadata。"""
    from src.agent.state import SearchTask, RetrievalMetadata
    from src.agent.nodes.research.search.tools import execute_document_search

    mock_results = [
        {
            "doc_id": "doc_001",
            "title": "函馆夜景攻略",
            "place_name": "函馆",
            "source": "",
            "score": 3.5,
            "snippet": "函馆山是观看夜景的最佳地点...",
        }
    ]

    mock_conn = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)

    mock_mgr = MagicMock()
    mock_mgr.search.return_value = mock_results

    with patch(
        "src.agent.nodes.research.search.tools.get_pool",
        new=AsyncMock(return_value=mock_pool),
    ), patch(
        "src.agent.nodes.research.search.docs.get_document_manager",
        new=AsyncMock(return_value=mock_mgr),
    ):
        task = SearchTask(
            tool_name="document_search",
            dimension="attraction",
            parameters={"query": "函馆夜景", "place_filter": "函馆"},
            rationale="test",
        )
        result = await execute_document_search(task)

    assert isinstance(result, RetrievalMetadata)
    assert result.payload["total"] == 1
    assert result.payload["docs"] == mock_results
    mock_mgr.search.assert_called_once_with("函馆夜景", "函馆")


@pytest.mark.priority("P0")
@pytest.mark.asyncio
async def test_document_search_missing_query():
    """缺少必填参数 query → ValueError。"""
    from src.agent.state import SearchTask
    from src.agent.nodes.research.search.tools import execute_document_search

    mock_conn = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_pool = MagicMock()
    mock_pool.acquire = MagicMock(return_value=mock_ctx)

    with patch(
        "src.agent.nodes.research.search.tools.get_pool",
        new=AsyncMock(return_value=mock_pool),
    ):
        task = SearchTask(
            tool_name="document_search",
            dimension="general",
            parameters={"place_filter": "东京"},
            rationale="test",
        )
        with pytest.raises(ValueError, match="缺少必填参数"):
            await execute_document_search(task)
