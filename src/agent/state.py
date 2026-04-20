"""
Module: src.agent.state
Responsibility: Defines the typed dictionaries for LangGraph state management.
Parent Module: src.agent
Dependencies: langgraph.graph.message.add_messages, langchain_core.messages.BaseMessage, typing

Constitutes the single source of truth for the multi-agent 'blackboard' memory,
flowing strictly from Router -> Analyzer -> Researcher -> etc.
"""

from typing import Annotated, TypedDict, Dict, Optional, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


# ==============================================================================
# Concrete Internal Models
# ==============================================================================

class UserProfileState(TypedDict):
    """
    Flattened User Profile representing the core conversational constraints.
    Persisted within the graph to maintain contextual consistency.
    """
    destination: Optional[list[str]]
    days: Optional[int]
    date: Optional[list[str]]
    people_count: Optional[int]
    budget_limit: Optional[int]
    accommodation: Optional[str]
    dining: Optional[str]
    transportation: Optional[str]
    pace: Optional[str]
    activities: Optional[list[str]]
    preferences: list[str]
    avoidances: list[str]

class RetrievalItem(TypedDict):
    """
    Standardized payload for knowledge graph/RAG hits. 
    TypedDict is strictly used here to avoid msgpack serialization crashes 
    during LangGraph checkpointing.
    """
    source: str
    title: str
    content: str
    link: Optional[str]
    metadata: Dict[str, Any]

# ==============================================================================
# Sub-State Compartments
# ==============================================================================

class SearchState(TypedDict):
    """
    Decoupled state slice strictly governing Researcher inputs/outputs.
    """
    query_history: Optional[list[str]]
    retrieval_context: Optional[str]
    retrieval_results: Optional[list[RetrievalItem]]
    retrieval_stats: Optional[Dict[str, int]]
    weather_info: Optional[str]  # Stores structured weather API dumps

class RecommenderState(TypedDict):
    """
    Decoupled state slice for recommendation items.
    """
    recommended_items: Optional[list[dict]]
    user_selected_items: Optional[list[dict]]

# ==============================================================================
# Global Graph Whiteboard
# ==============================================================================

class TravelState(TypedDict):
    """
    Global root state for the multi-agent graph system.
    Propagated dynamically across node thresholds.
    """
    # LangGraph message history aggregating conversation turns
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Intention routed by Router
    latest_intent: Optional[str]
    
    # Internal trigger flag manipulated by Analyzer to govern Researcher execution
    needs_research: bool
    
    # Sub-compartmentalized profile traits
    user_profile: Optional[UserProfileState]
    
    # Sub-compartmentalized external knowledge acquisitions
    search_data: Optional[SearchState]
    
    # Sub-compartmentalized user itinerary selections
    recommender_data: Optional[RecommenderState]
