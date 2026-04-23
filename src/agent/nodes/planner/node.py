"""
Module: src.agent.nodes.planner.node
Responsibility: Breaks down high-level user requests into granular research tasks.
"""

from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.agent.state.state import TravelState
from src.agent.state.schema import TraceLog, ResearchManifest, ResearchTask
from src.utils.llm_factory import LLMFactory

class PlannerOutput(BaseModel):
    """Structured output from the planner node."""
    tasks: list[ResearchTask] = Field(description="List of specific research tasks to be executed")
    reasoning: str = Field(description="The thought process behind why these tasks are needed")

PLANNER_PROMPT = """你是一个专业的旅游行程规划架构师。你的任务是将用户的旅游偏好拆解为多个独立的、可执行的调研任务。

用户信息:
{user_profile}

当前请求:
{user_request}

已知上下文:
{context}

请生成一个任务清单，每个任务应具有明确的目标。任务类型包括：
1. TRANSPORT: 研究航班、高铁等大交通。
2. LODGING: 研究酒店、民宿。
3. ATTRACTION: 研究景点门票、开放时间。
4. DINING: 研究当地特色餐饮。
5. LOGISTICS: 研究当地市内交通（地铁、租车）。

要求：
- 任务必须具体，例如“查询5月1日从上海到东京的直飞航班”而非“看交通”。
- 尽可能利用用户已提供的偏好（如预算、酒店偏好）。
- 如果信息基本完整，可以开始生成任务；如果你认为还需要更多信息，可以只生成初步的调研任务。

输出必须符合 JSON 格式。"""

async def planner_node(state: TravelState) -> dict:
    start_time = datetime.now()
    llm = LLMFactory.get_model("gpt-4o") # 规划需要较强的逻辑能力
    structured_llm = llm.with_structured_output(PlannerOutput)
    
    prompt = ChatPromptTemplate.from_template(PLANNER_PROMPT)
    chain = prompt | structured_llm
    
    result = await chain.ainvoke({
        "user_profile": state["user_profile"].model_dump(),
        "user_request": state["user_request"],
        "context": "N/A" # 暂时没有更深的上下文
    })
    
    # 构造研究清单
    manifest = ResearchManifest(
        tasks=result.tasks,
        status="PENDING",
        created_at=datetime.now().isoformat()
    )
    
    latency = int((datetime.now() - start_time).total_seconds() * 1000)
    trace = TraceLog(node="planner", status="SUCCESS", latency_ms=latency)
    
    return {
        "research_manifest": manifest,
        "trace_history": [trace]
    }
