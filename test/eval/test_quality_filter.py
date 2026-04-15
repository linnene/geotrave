import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from agent.nodes.researcher.tools import ResearcherTools
from agent.state import RetrievalItem


@pytest.mark.asyncio
async def test_filter_retrieval_items():
    """
    测试二级质检过滤功能能否正确标记不相关的项目，
    并能够准确拦截和区分。
    """
    # 模拟输入数据
    items = [
        RetrievalItem(
            source="web",
            title="【昆明旅游】最佳海鸥观赏点",
            content="昆明滇池的海鸥每年冬天都会飞来...",
            link="http://example.com/seagull",
            metadata={"query": "昆明 景点推荐"}
        ),
        RetrievalItem(
            source="web",
            title="淘宝特惠大甩卖",
            content="不要998，只要98！赶紧点击进入...",
            link="http://example.com/spam",
            metadata={"query": "昆明 景点推荐"}
        )
    ]
    
    # 构造一个假的 LLM
    mock_llm = MagicMock()
    
    # 我们期望 LLM 根据规则，对于第一条回答 YES，第二条回答 NO
    async def mock_ainvoke(prompt_obj):
        content = prompt_obj if isinstance(prompt_obj, str) else prompt_obj.text
        # 如果 prompt 中出现了淘宝/大甩卖，返回 NO，否则返回 YES
        if "大甩卖" in content:
            return MagicMock(content="NO")
        else:
            return MagicMock(content="YES")
            
    mock_llm.ainvoke = mock_ainvoke

    # 调用工具类进行过滤
    filtered_items = await ResearcherTools.filter_retrieval_items(items, mock_llm)
    
    # 断言列表长度与内容
    assert len(filtered_items) == 1, "应该返回1条，另一条应该被丢弃"
    
    # 验证第一条是否正常放行
    assert filtered_items[0].get("title") == "【昆明旅游】最佳海鸥观赏点"

