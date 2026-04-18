"""
Researcher Tools: Supporting retrieval logic for the Researcher Node.
"""

import json
from typing import List, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import HumanMessage

from agent.state import TravelState, RetrievalItem
from agent.schema import ResearchPlan
from utils.prompt import research_query_prompt_template, research_filter_prompt_template
from utils.logger import logger

class ResearcherTools:
    """
    Collection of static methods for multi-source retrieval tasks.
    """

    @staticmethod
    async def generate_research_plan(state: TravelState, llm: BaseChatModel) -> Optional[ResearchPlan]:
        """
        Analyze user profile and history to generate a structured search plan.
        """
        profile = state.get("user_profile") or {}
        messages = state.get("messages", [])
        
        # Extract recent conversation snippets for focus
        recent_context = ""
        if messages:
            recent_context = "\n".join([f"{m.type}: {m.content}" for m in messages[-3:]])

        try:
            parser = PydanticOutputParser(pydantic_object=ResearchPlan)
            
            # Use safety get for dictionary fields to avoid KeyError
            prompt_value = research_query_prompt_template.format(
                destination=profile.get("destination", []),
                days=profile.get("days"),
                people_count=profile.get("people_count", 1),
                date=profile.get("date"),
                budget_limit=profile.get("budget_limit", 0),
                accommodation=profile.get("accommodation"),
                dining=profile.get("dining"),
                transportation=profile.get("transportation"),
                pace=profile.get("pace"),
                activities=profile.get("activities", []),
                preferences=profile.get("preferences", []),
                avoidances=profile.get("avoidances", []),
                recent_context=recent_context,
                format_instructions=parser.get_format_instructions()
            )

            chain = llm | parser
            plan = await chain.ainvoke(prompt_value)
            
            # Logic override: Always need weather if destination is valid
            if profile.get("destination"):
                plan.need_weather = True
                
            return plan
        except Exception as e:
            logger.error(f"[Researcher Tools] Plan generation error: {e}")
            return None

    @staticmethod
    async def search_local_kt(query: str) -> List[RetrievalItem]:
        """
        Simulate/Invoke Local Vector DB (Knowledge Base) search.
        """
        logger.info(f"[Tool: LocalSearch] Query: {query}")
        # Placeholder for real vector search call
        return [
            {
                "source": "local_kb",
                "title": f"Local Tips for {query}",
                "content": f"Structured guide content from inner knowledge about {query}.",
                "link": None,
                "metadata": {"score": 0.95}
            }
        ]

    @staticmethod
    async def search_web_ddg(query: str, max_results: int = 5) -> List[RetrievalItem]:
        """
        Simulate/Invoke Web Search (e.g., DuckDuckGo, Bing).
        """
        logger.info(f"[Tool: WebSearch] Query: {query}")
        # Placeholder for real web search call
        return [
            {
                "source": "web",
                "title": f"Web Result: Scenic spots in {query}",
                "content": f"Discover top-rated travel destinations and reviews for {query} on the web.",
                "link": "https://example.com/travel",
                "metadata": {"relevance": "high"}
            }
        ]

    @staticmethod
    async def search_weather_openmeteo(location: str, start_date: str = None, end_date: str = None) -> List[RetrievalItem]:
        """
        Simulate/Invoke Weather API for a specific location and date range.
        """
        logger.info(f"[Tool: WeatherAPI] Loc: {location}, Dates: {start_date} to {end_date}")
        # Placeholder for real weather API
        desc = "Partly cloudy, 18-24C" if not start_date else f"Forecast for {start_date}: Sunny, 22C"
        return [
            {
                "source": "api_weather",
                "title": f"Weather for {location}",
                "content": desc,
                "link": "https://open-meteo.com",
                "metadata": {"temp_unit": "celsius"}
            }
        ]

    @staticmethod
    async def filter_retrieval_items(items: List[RetrievalItem], llm: BaseChatModel) -> List[RetrievalItem]:
        """
        Quick LLM-based filtering to remove irrelevant snippets.
        """
        # Batching or individual filtering can be done here. 
        # For efficiency, we keep only original list for now (placeholder).
        return items