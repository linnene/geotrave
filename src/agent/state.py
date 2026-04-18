from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing import Annotated, TypedDict, List, Dict, Optional, Any

# ----------------- Core Models -----------------

class UserProfileState(TypedDict):
    """
    Flattened user profile (Base info + Minor preferences).
    """
    destination: list[str]
    days: int | None
    date: list[str] | None
    people_count: int | None
    budget_limit: int | None
    accommodation: str | None
    dining: str | None
    transportation: str | None
    pace: str | None
    activities: list[str]
    preferences: list[str]
    avoidances: list[str]

class RetrievalItem(TypedDict):
    """
    Single retrieval result item.
    """
    source: str
    title: str
    content: str
    link: Optional[str]
    metadata: Dict[str, Any]

# ----------------- Shared State -----------------

class SearchState(TypedDict):
    """
    Decoupled private search state.
    """
    query_history: list[str]
    retrieval_context: str | None
    retrieval_results: list[RetrievalItem]
    retrieval_stats: Dict[str, int]
    weather_info: str | None

class RecommenderState(TypedDict):
    """
    Decoupled private recommendation state.
    """
    recommended_items: list[dict]
    user_selected_items: list[dict]


class TravelState(TypedDict):
    """
    Global state whiteboard.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Latest intent identified by Router
    latest_intent: str | None
    
    # Research flag decided by Analyzer
    needs_research: bool
    
    # User requirements profile
    user_profile: UserProfileState | None
    
    # Retrieval data
    search_data: SearchState | None
    
    # Recommendation data
    recommender_data: RecommenderState | None

def get_initial_state() -> dict:
    """
    Returns a dictionary representing the initial values for the state.
    """
    return {
        "messages": [],
        "latest_intent": None,
        "needs_research": False,
        "user_profile": {
            "destination": [],
            "days": None,
            "date": None,
            "people_count": None,
            "budget_limit": None,
            "accommodation": None,
            "dining": None,
            "transportation": None,
            "pace": None,
            "activities": [],
            "preferences": [],
            "avoidances": []
        },
        "search_data": {
            "query_history": [],
            "retrieval_results": [],
            "retrieval_stats": {},
            "retrieval_context": None,
            "weather_info": None
        },
        "recommender_data": {
            "recommended_items": [],
            "user_selected_items": []
        }
    }