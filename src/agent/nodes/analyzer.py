# Analyzer Node: Extracting Travel Information from User Conversations

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from langchain_core.output_parsers import PydanticOutputParser

from agent.state import TravelState, TravelInfo

from utils.config import (
    OPENAI_API_KEY, 
    MODEL_BASE_URL, 
    MODEL_ID,
    PLANNING_TEMPERATURE,
    MAX_TOKENS,
    LLM_TIMEOUT
)

from utils.prompt import analyzer_prompt_template

# Init Analyzer`s LLM
llm = ChatOpenAI(
    model=MODEL_ID,
    api_key=SecretStr(OPENAI_API_KEY), 
    base_url=MODEL_BASE_URL, 
    temperature=PLANNING_TEMPERATURE,
    max_completion_tokens=MAX_TOKENS,  
    timeout=LLM_TIMEOUT,                  
    disable_streaming=True,
)

# Analyzer Node
async def analyzer_node(state: TravelState):

    last_message = state["messages"][-1].content
    
    parser = PydanticOutputParser(pydantic_object=TravelInfo)
    
    # prompt 注入
    prompt_value = analyzer_prompt_template.format(
        last_message=last_message,
        format_instructions=parser.get_format_instructions()
    )
    
    # 组装 LCEL 链：LLM 生成文本 -> parser 转化为对象
    chain = llm | parser
    result = await chain.ainvoke(prompt_value)
    
    # write back to shared state
    return {
        "messages": [AIMessage(content=result.reply)],
        "destination": result.destination,
        "days": result.days,
        "budget": result.budget,
    }