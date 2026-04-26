import time
import json
from typing import Dict, Any

from src.agent.state import TraceLog, TravelState, QueryGeneratorOutput, ResearchManifest
from src.utils.llm_factory import LLMFactory
from src.utils.prompt import query_generator_prompt_template
from src.utils.logger import get_logger
from src.agent.nodes.utils import format_recent_history
from .config import TEMPERATURE, HISTORY_LIMIT, MAX_TOKENS

logger = get_logger("QueryGeneratorNode")

def _get_format_instructions() -> str:
    """Extracts and formats the JSON schema from QueryGeneratorOutput for LLM guidance."""
    return json.dumps(QueryGeneratorOutput.model_json_schema(), indent=2, ensure_ascii=False)

def _get_tools_documentation() -> str:
    """
    TODO: 之后这里应该从一个统一的工具注册中心动态获取文档。
    目前先提供一个结构化的占位符，演示注入逻辑。
    """
    # 模拟从 LangChain 工具对象中提取 metadata
    tools = [
        {
            "name": "web_search",
            "description": "搜索互联网获取最新旅游信息、攻略、评价等。",
            "parameters": {
                "query": "string (搜索关键词)"
            }
        },
        {
            "name": "vector_db",
            "description": "查询本地旅游知识库，获取结构化的景点、餐厅、酒店底表信息。",
            "parameters": {
                "query": "string (检索指令)",
                "collection": "string (可选: attractions, restaurants, hotels)"
            }
        }
    ]
    return json.dumps(tools, indent=2, ensure_ascii=False)

async def query_generator_node(state: TravelState) -> Dict[str, Any]:
    """
    Query Generator Node.
    Analyzes user profile and request to create a structured multi-dimensional research plan.
    """
    start_time = time.time()
    logger.info("Generating research plan at [QueryGenerator]...")

    # 1. Prepare Context (注入最近 HISTORY_LIMIT 轮对话历史)
    messages = state.get("messages", [])
    
    # 使用解耦的历史格式化工具
    history = format_recent_history(messages, HISTORY_LIMIT)

    user_profile = state.get("user_profile")
    user_request = state.get("user_request", "无明确诉求")
    
    # 2. Dynamic Injection
    tools_doc = _get_tools_documentation()
    format_instructions = _get_format_instructions()
    
    prompt_str = query_generator_prompt_template.format(
        user_profile=user_profile.model_dump_json(indent=2) if user_profile else "{}",
        user_request=user_request,
        tools_doc=tools_doc,
        format_instructions=format_instructions,
        history=history,
        missing_fields=", ".join(state.get("missing_fields", [])) if state.get("missing_fields") else "无核心缺失"
    )

    # 3. LLM Orchestration
    llm = LLMFactory.get_model("QueryGenerator", temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
    bound_llm = llm.bind(response_format={"type": "json_object"})

    try:
        raw_result = await bound_llm.ainvoke(prompt_str)
        
        # 处理可能的多种 content 类型 (BaseMessage.content 可以是 str 或 list)
        raw_content = raw_result.content if hasattr(raw_result, "content") else str(raw_result)
        
        if isinstance(raw_content, list):
            # 将列表中的文本块合并
            content = "".join([
                t.get("text", "") if isinstance(t, dict) else str(t) 
                for t in raw_content
            ])
        else:
            content = str(raw_content)

        parsed_json = json.loads(content)
        result = QueryGeneratorOutput(**parsed_json)
        
        # 4. Update ResearchManifest
        # 将生成的任务转换为 ResearchManifest 能理解的列表
        # TODO: 之后的 ResearchManifest 可能会演进为存储整个 Task 对象
        active_queries = []
        for task in result.tasks:
            active_queries.append(f"[{task.tool_name}] {task.dimension}: {json.dumps(task.parameters, ensure_ascii=False)}")

        new_research_data = ResearchManifest(
            active_queries=active_queries,
            verified_results=[], # 新一轮生成清空旧的（或增量，取决于策略）
            feedback_history=[]
        )

        trace = TraceLog(
            node="query_generator",
            status="SUCCESS",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={
                "task_count": len(result.tasks),
                "strategy": result.research_strategy
            }
        )

        return {
            "research_data": new_research_data,
            "trace_history": [trace]
        }

    except Exception as e:
        logger.error(f"QueryGenerator execution failed: {str(e)}", exc_info=True)
        trace = TraceLog(
            node="query_generator",
            status="FAIL",
            latency_ms=int((time.time() - start_time) * 1000),
            detail={"error": str(e)}
        )
        return {"trace_history": [trace]}
