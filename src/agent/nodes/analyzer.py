from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr
from langchain_core.output_parsers import PydanticOutputParser

from src.agent.state import TravelState

from src.utils.config import (
    OPENAI_API_KEY, 
    MODEL_BASE_URL, 
    MODEL_ID,
    PLANNING_TEMPERATURE,
    MAX_TOKENS,
    TIMEOUT
)

from src.utils.prompt import analyzer_prompt_template

# 定义分析师要提取的数据卡板
class TravelInfo(BaseModel):
    destination: str | None = Field(default=None, description="旅行目的地，如果没有则为None")
    days: int | None = Field(default=None, description="旅行天数，如果没有则为None")
    budget: int | None = Field(default=None, description="旅行总预算")

    reply: str = Field(description="如果你提取到了所有信息，回复'好的，这就为您收集去{destination}{days}天的资料！'；如果信息不全，请客气地像导游一样追问缺失的信息。")

# 初始化分析师专用的 LLM
llm = ChatOpenAI(
    model=MODEL_ID,
    api_key=SecretStr(OPENAI_API_KEY), 
    base_url=MODEL_BASE_URL, 
    temperature=PLANNING_TEMPERATURE,
    max_completion_tokens=MAX_TOKENS,  
    timeout=TIMEOUT,                  
    disable_streaming=True,
)

# 分析师节点逻辑
async def analyzer_node(state: TravelState):
    
    """
    负责从用户的历史对话中提取目的地、天数和预算，如果信息不全则提示追问。
    """

    last_message = state["messages"][-1].content
    
    parser = PydanticOutputParser(pydantic_object=TravelInfo)
    
    # 使用从专门的 prompt 文件中导入的 Template
    prompt_value = analyzer_prompt_template.format(
        last_message=last_message,
        format_instructions=parser.get_format_instructions()
    )
    
    # 组装 LCEL 链：LLM 生成文本 -> parser 转化为对象
    chain = llm | parser
    result = await chain.ainvoke(prompt_value)
    
    # 将提取成果写回流转用的白板 state
    return {
        "messages": [AIMessage(content=result.reply)],
        "destination": result.destination,
        "days": result.days,
        "budget": result.budget,
    }