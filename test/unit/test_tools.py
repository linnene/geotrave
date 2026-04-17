import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from agent.nodes.researcher.tools import ResearcherTools
from agent.schema import ResearchPlan
from langchain_core.messages import AIMessage

# Ensure we can import from src
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

@pytest.mark.asyncio
async def test_weather_api_integration():
    """测试 Open-Meteo API 的联通性、经纬度转换及天气结果解析"""
    # 模拟 geocoding 和 weather api 的响应
    mock_geo_data = {
        "results": [{"latitude": 25.6, "longitude": 100.2, "name": "Dali"}]
    }
    mock_weather_data = {
        "daily": {
            "time": ["2024-05-01"],
            "temperature_2m_max": [25.0],
            "temperature_2m_min": [15.0],
            "weathercode": [0]
        }
    }
    
    # 模拟 urllib.request.urlopen
    # 需要在 patch 的路径上完全匹配 researcher.tools 里的导入方式
    with patch("urllib.request.urlopen") as mock_url:
        # Mock 1: Geocoding
        mock_res_geo = MagicMock()
        mock_res_geo.read.return_value = json.dumps(mock_geo_data).encode()
        mock_res_geo.__enter__.return_value = mock_res_geo
        
        # Mock 2: Weather
        mock_res_weather = MagicMock()
        mock_res_weather.read.return_value = json.dumps(mock_weather_data).encode()
        mock_res_weather.__enter__.return_value = mock_res_weather
        
        mock_url.side_effect = [mock_res_geo, mock_res_weather]
        
        result = await ResearcherTools.search_weather_openmeteo("大理", "2024-05-01", "2024-05-01")
        
        assert len(result) == 1
        assert "Dali" in result[0]["title"]
        assert "25.0" in result[0]["content"]
        assert "15.0" in result[0]["content"]

@pytest.mark.asyncio
async def test_web_search_ddg_resilience():
    """测试 DuckDuckGo 搜索模块在网络波动下的重试与解析逻辑"""
    # 由于 DDGS 是在 search_web_ddg 函数内部 import 的
    # 我们直接 patch 'ddgs.DDGS' 这个全局入口
    with patch("ddgs.DDGS") as mock_ddgs_class:
        mock_instance = mock_ddgs_class.return_value.__enter__.return_value
        mock_instance.text.return_value = [
            {"title": "大理古城攻略", "body": "大理古城是个好地方", "href": "http://example.com"}
        ]
        
        result = await ResearcherTools.search_web_ddg("大理 攻略")
        
        assert len(result) == 1
        assert result[0]["title"] == "大理古城攻略"
        assert result[0]["source"] == "web"

@pytest.mark.asyncio
async def test_vector_db_retrieval():
    """测试与本地 ChromaDB 的检索集成"""
    class MockDoc:
        page_content = "这里是大理苍山感悟。"

    with patch("agent.nodes.researcher.tools.search_similar_documents", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [MockDoc()]
        
        result = await ResearcherTools.search_local_kt("大理 景点")
        
        assert len(result) == 1
        assert "感悟" in result[0]["content"]
        assert result[0]["source"] == "local"

@pytest.mark.asyncio
async def test_researcher_plan_generation_logic():
    """测试生成研究计划的能力"""
    state = {
        "user_profile": {"destination": "大理", "days": 5},
        "messages": []
    }
    
    mock_llm = AsyncMock()
    # 模拟 LLM 返回符合 Pydantic 结构的 JSON 文本，包含天气
    mock_llm.ainvoke.return_value = AIMessage(content='{"local_query": "大理 攻略", "web_queries": ["大理 景点"], "need_weather": true}')
    
    plan = await ResearcherTools.generate_research_plan(state, mock_llm)
    
    assert plan is not None
    assert plan.local_query == "大理 攻略"
    assert plan.need_weather is True

@pytest.mark.asyncio
async def test_researcher_filter_logic_item():
    """测试通过 LLM 过滤杂讯条目"""
    items = [
        {"title": "大理攻略", "content": "大理好玩", "metadata": {"query": "大理"}},
        {"title": "抽奖", "content": "中大奖", "metadata": {"query": "大理"}}
    ]
    
    mock_llm = AsyncMock()
    mock_llm.ainvoke.side_effect = [
        AIMessage(content="YES"),
        AIMessage(content="NO")
    ]
    
    filtered = await ResearcherTools.filter_retrieval_items(items, mock_llm)
    
    assert len(filtered) == 1
    assert filtered[0]["title"] == "大理攻略"

