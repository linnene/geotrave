from typing import List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agent.state import TravelState
from utils.logger import logger
from utils.prompt import filter_prompt_template
from utils.config import (
    FILTER_MODEL_API_KEY,
    FILTER_MODEL_BASE_URL,
    FILTER_MODEL_ID,
    MAX_TOKENS,
    LLM_TIMEOUT
)

# 使用 Filter 专属模型配置
guard_llm = ChatOpenAI(
    model=FILTER_MODEL_ID,
    api_key=SecretStr(FILTER_MODEL_API_KEY),
    base_url=FILTER_MODEL_BASE_URL,
    temperature=0, # 判定逻辑需要高度一致性
    max_completion_tokens=MAX_TOKENS,
    timeout=LLM_TIMEOUT,
    disable_streaming=True
)

class EvaluationResult(BaseModel):
    """单条检索结果的判定模型"""
    is_safe: bool = Field(..., description="内容是否合规、无违禁信息、无色情/暴力内容")
    is_relevant: bool = Field(..., description="内容是否与原始检索词及旅行目的地相关")

class FilterResponse(BaseModel):
    """整体判定的响应模型"""
    evaluations: List[EvaluationResult] = Field(..., description="针对各部分检索内容的判定列表")


def filter_node(state: TravelState):
    """
    过滤器节点：对 Researcher 的 `retrieval_context` 进行内容判定与过滤。
    """
    context = state.get("retrieval_context")
    if not context or "retrieval skipped" in context:
        return {"retrieval_context": context}

    logger.info("[Filter Node] Starting content evaluation and filtering...")

    try:
        # 降级方案：不再强制使用 with_structured_output，因为它在部分模型/API 上可能不受支持 (400 错误)
        # 改用普通的解析方式
        from langchain_core.output_parsers import PydanticOutputParser
        parser = PydanticOutputParser(pydantic_object=FilterResponse)
        
        # 将格式指令注入提示词（如果需要，或者直接调用 invoke）
        chain = filter_prompt_template | guard_llm | parser
        
        # 将原始 context 传入
        eval_result: FilterResponse = chain.invoke({
            "retrieval_context": context,
            "format_instructions": parser.get_format_instructions()
        }) # type: ignore

        # 逻辑：将 context 按来源拆分处理比较复杂，目前采取“整块判定”或“按行过滤预览”
        # 优化：Researcher 节点输出格式为：
        # ### Local Knowledge Base: ...
        # ### Web Search Results: Q: ... A: ... --- Q: ... A: ...
        
        sections = context.split("---") # Web 结果的拆分符
        filtered_web_results = []
        
        # 简单逻辑：如果某一部分被判定为不安全或不相关，则剔除
        # 这里为了简化，如果 eval_result 中的某一项失败，我们记录它
        valid_sections = []
        dropped_sections = []
        for i, section in enumerate(sections):
            # 获取对应的判定证据（如果判定列表长度匹配）
            if i < len(eval_result.evaluations):
                res = eval_result.evaluations[i]
                if res.is_safe and res.is_relevant:
                    valid_sections.append(section)
                else:
                    logger.warning(f"[Filter Node] Dropping unsafe/irrelevant section.")
                    logger.debug(f"[Filter Node] Filtered Content: {section}")
                    dropped_sections.append(section)
            else:
                # 默认保留（防止模型输出列表长度不符）
                valid_sections.append(section)

        if not valid_sections:
            logger.error("[Filter Node] ALL search results filtered out due to safety or relevance issues.")
            return {
                "retrieval_context": "Warning: All search results were filtered due to safety or relevance concerns.",
                "filtered_context": "---".join(dropped_sections) if dropped_sections else None
            }

        new_context = "---".join(valid_sections)
        logger.info("[Filter Node] Filtering complete.")
        return {
            "retrieval_context": new_context,
            "filtered_context": "---".join(dropped_sections) if dropped_sections else None
        }

    except Exception as e:
        logger.error(f"[Filter Node] Error during filtering: {e}")
        # 出错时保底保留原内容，但在日志报警
        return {"retrieval_context": context}
